# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 MbitAI — see NOTICE for attribution.
from seclog.metrics import fga, fta, grouping_accuracy, parsing_accuracy, score_all


def test_perfect_match():
    gt_ids = ["A", "A", "B", "B"]
    parsed_ids = ["x", "x", "y", "y"]
    gt_t = ["foo <*>", "foo <*>", "bar", "bar"]
    parsed_t = ["foo <*>", "foo <*>", "bar", "bar"]
    s = score_all(gt_ids, parsed_ids, gt_t, parsed_t)
    assert s["GA"] == 1.0
    assert s["PA"] == 1.0
    assert s["FGA"] == 1.0
    assert s["FTA"] == 1.0


def test_ga_penalizes_split_group():
    gt_ids = ["A", "A", "A"]
    parsed_ids = ["x", "x", "y"]
    assert grouping_accuracy(gt_ids, parsed_ids) == 0.0


def test_pa_token_mismatch():
    assert parsing_accuracy(["a <*> b"], ["a b"]) == 0.0
    assert parsing_accuracy(["a   <*>"], ["a <*>"]) == 1.0


def test_fga_template_level_not_message_level():
    gt_ids = ["A", "A", "A", "B"]
    parsed_ids = ["x", "x", "y", "z"]
    ga = grouping_accuracy(gt_ids, parsed_ids)
    assert ga == 0.25
    assert abs(fga(gt_ids, parsed_ids) - 0.4) < 1e-9


def test_fta_requires_token_match():
    gt_ids = ["A", "A"]
    parsed_ids = ["x", "x"]
    gt_t = ["const <*>", "const <*>"]
    parsed_wrong = ["const", "const"]
    parsed_ok = ["const <*>", "const <*>"]
    assert fta(gt_ids, parsed_ids, gt_t, parsed_wrong) == 0.0
    assert fta(gt_ids, parsed_ids, gt_t, parsed_ok) == 1.0


def test_fta_counts_pure_split_with_matching_tokens():
    # One ground-truth template split into two parsed clusters. Both
    # clusters are pure and their tokens match, so the template counts
    # once (Jiang et al., ISSTA'24 §4.2.2). Set-equality would score 0.
    gt_ids = ["A", "A", "A"]
    parsed_ids = ["x", "x", "y"]
    gt_t = ["k <*>", "k <*>", "k <*>"]
    parsed_t = ["k <*>", "k <*>", "k <*>"]
    assert fta(gt_ids, parsed_ids, gt_t, parsed_t) == 1.0


def test_fta_rejects_mixed_template():
    # A parsed template spanning two ground-truth templates is not
    # correctly identified, even though its tokens match one of them.
    gt_ids = ["A", "B"]
    parsed_ids = ["x", "x"]
    gt_t = ["k <*>", "j <*>"]
    parsed_t = ["k <*>", "k <*>"]
    assert fta(gt_ids, parsed_ids, gt_t, parsed_t) == 0.0
