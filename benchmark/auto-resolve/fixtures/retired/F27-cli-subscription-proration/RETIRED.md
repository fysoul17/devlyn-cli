# Retired: F27 CLI subscription proration

Retired from the active golden suite after headroom smoke
`20260511-f27-headroom-smoke-061401`.

Reason: `solo_claude` scored 94, exceeding the headroom ceiling of 80, while
`bare` scored 33 and passed only 1 of 3 verification commands. The fixture is
too explicit for current solo/pair lift measurement and too expensive to keep
in the default suite.

Future use: rework the visible contract so it creates a fair pair-risk-probe
gap, or replace it with a different billing fixture. Do not count this fixture
as pair evidence in its current form.
