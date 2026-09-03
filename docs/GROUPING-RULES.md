# SecOps-2k grouping rules

Two grouping variants ship for every line, following the pattern of the
corrected LogHub re-release (Zenodo 20752471, Jun 2026): a **tight**
grouping and a **loose** grouping. The machine-readable map is
`configs/grouping.yaml`. This file is the human-readable rulebook.

## Rule 0. What a template is

A template is the constant part of a log line. Every run-time value
(username, IP, port, pid, path, command) is replaced by `<*>`.
`ParameterList` records the values in order. Two lines share a tight
template if and only if their constant tokens match exactly.

## Tight rules (25 templates)

1. Outcome stays constant. `Failed password` and `Accepted password`
   are different tight templates even though the line shape is identical.
2. `invalid user` stays constant. `Failed password for invalid user …`
   (S02) is a different tight template from `Failed password for …`
   (S01). Same for `Invalid user …` (S05) vs `input_userauth_request:
   invalid user …` (S12).
3. Process stays constant. `pam_unix(sshd:auth)` (S08/S09) and
   `pam_unix(sudo:session)` (U01/U02) never merge, even with similar
   wording.
4. UFW action and protocol stay constant. `BLOCK` vs `ALLOW` and
   `TCP` vs `UDP` vs `ICMP` split tight templates (F01–F04).
5. The auditd event type stays constant. `USER_AUTH` (A01) vs `USER_LOGIN`
   (A02) stay separate.
6. Static suffixes stay constant. `[preauth]`, `:11:`, `ssh2`,
   `OUT=`, `exe=/usr/sbin/sshd` are part of the template.

## Loose rules (10 groups)

Loose merges tight templates that describe the same security event from
different daemon lines. It changes the grouping and nothing else.
`EventTemplate` strings are identical in both files, so PA is the same
and GA/FGA show the grouping effect.

| Loose group | Tight members | Rule |
|---|---|---|
| L_AUTH_FAIL | S01, S02, S08, S09, S13 | any failed authentication outcome |
| L_AUTH_OK | S03, S04 | any successful login, either method |
| L_PROBE | S05, S12 | username enumeration (invalid-user lines) |
| L_SESS_END | S06, S07, S10, S14 | teardown before auth completes |
| L_INTRUSION | S11 | reverse-DNS break-in warning, kept separate (rare, distinct) |
| L_SUDO_OK | U01, U02 | completed sudo session (open/close pair) |
| L_SUDO_DENY | U03, U04, U05 | denied or failed privilege escalation |
| L_FW_BLOCK | F01, F02, F04 | blocked packet, any protocol |
| L_FW_ALLOW | F03 | allowed packet |
| L_AUDIT | A01, A02 | auditd identity event |

## Worked example

These three lines are three tight templates but one loose group:

```text
Failed password for root from 203.0.113.7 port 51234 ssh2            -> S01 -> L_AUTH_FAIL
Failed password for invalid user admin from 203.0.113.7 port 51235 ssh2 -> S02 -> L_AUTH_FAIL
pam_unix(sshd:auth): authentication failure; ... rhost=203.0.113.7  -> S08 -> L_AUTH_FAIL
```

## Imbalance note

Common templates (S01 failed passwords, S08 pam failures, F01 TCP
blocks) dominate, and rare ones (S11 break-in warning, S13 max attempts,
U03/U05 denials) get few lines. That mirrors real auth logs, and it
reproduces the LogHub-2.0 finding that GA hides failures on rare
templates. Report FGA and FTA next to GA, always.
