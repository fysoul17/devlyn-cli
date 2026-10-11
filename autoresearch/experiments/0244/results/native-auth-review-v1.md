# Native same-account renewal review v1

Verdict: SHIP for the bounded, authorized operator renewal. No remaining CRITICAL or HIGH finding. This is an authentication concurrency/source review, not a research dispatch or efficacy approval.

Reviewer: /root/review_0242. Static read-only review; no authentication, network, native model, or test execution by this reviewer. Reviewed the installed Claude 2.1.296 embedded source and the corrected private renew.cjs. The earlier concrete HIGH finding (concurrent login detection omitted the versioned native executable) is resolved: the predicate now recognizes both the claude alias and versions/X.Y.Z login commands, including optional prerelease suffixes. Parent reports syntax validation and eight targeted predicate contrasts passed; those checks were not rerun here.

The native auth login refresh-token/scopes environment branch calls the official native grant and persistence path and bypasses browser login. This branch does not itself take the normal automatic-refresh locks. The wrapper therefore takes both compatible proper-lockfile 4.1.2 leases before reading the host grant: ~/.claude/.oauth_refresh.lock and realpath(~/.claude)+'.lock', with realpath:false, stale:60000 and update:5000. The installed source resolves the unoverridden default storage directory to ~/.claude; the wrapper rejects storage and relevant auth overrides. It retains both leases through the post-renewal profile read.

The wrapper checks for known non-cooperating keeper/login writers and benchmark containers, reads the current grant only after acquiring both leases, checks account and organization fingerprints against the frozen runtime, and passes the existing refresh token and scopes through child environment only. Only the official native CLI persists credentials. The post-read checks identity, scopes, success indication and the unchanged 6300-second lifetime requirement. Logs contain controlled metadata/hashes rather than credentials or raw native output/errors. There is no manual Keychain overwrite or old-grant restoration.

If a lease is compromised during the native request, that already-issued operation is allowed to finish, then the workflow fails at the guard. This cannot undo a grant already rotated upstream; allowing native persistence to complete and refusing further workflow is the appropriate bounded tradeoff. The locks coordinate compatible automatic refreshers; they cannot exclude a newly launched non-cooperating login or a remote copied-grant writer. The operator must retain the established no-new-login/no-keeper condition while this bounded operation runs. No generic authentication framework or legacy custom refresh helper is introduced.

Scope: private operator script only. A successful renewal still requires the unchanged study preflight before any benchmark dispatch. Historical STOP and NOT_DISPATCHED records remain intact.

SHA-256 bindings:

| File | SHA-256 |
| --- | --- |
| renew.cjs | d8400df438d9ecd5695a8a3d80fc9d92a306d745f40d716b25c4e05a6a0c6c7d |
| package.json | 368a9c3f2804db4fbf028286a950734041d110474404df93a6ff74991aaf3dfa |
| package-lock.json | a3d2a43eaace35f0fff517261cd9bed5a62d829611c8cd09e6e86a5c1fb5d36c |
| node_modules/proper-lockfile/package.json | 23888ecc7abd83a8e98e132da556eda2172792cc04c4e6d157b590667802bd2a |

Principles: No guesswork (installed source and exact bytes checked), Best practice (standard native-compatible leases), No workaround (native grant/persistence, unchanged account and margin), No overengineering (bounded operator action), Production ready (explicit failure, no credential rollback).
