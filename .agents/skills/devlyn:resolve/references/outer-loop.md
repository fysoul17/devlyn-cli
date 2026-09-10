# Outer-loop commit boundary

A full `/devlyn:resolve` run starts only from committed owner inputs. Keep each
commit scoped: no unrelated paths or queue-item changes.

1. Before task writes, the outer owner allocates an absent task branch per
   [task completion](task-completion.md); linked worktree allocation is optional.
   Never adopt a pre-existing task branch. Before an item's first full run, commit the current queue-item delta, when
   applicable, together with its linked spec bundle. For conversational work,
   commit the agreed spec bundle before the full run.
2. When findings require an accepted verification amendment, commit only that
   linked spec-bundle amendment before rerunning the item.
3. After a terminal result, commit the current item's `[x]` or `[F]` queue
   transition before starting the next pending item.
4. After mandatory successful normal-run archive and any terminal queue commit,
   the outer owner completes delivery once per [task completion](task-completion.md).
   Bind the verified source and declared queue-only commit separately. Failed or
   verify-only runs do not publish; local-only/no-push wins. Pending delivery
   retains its workspace and never changes the product verdict.

Drain strictly serially. Bootstrap and resolve never make these owner commits;
the outer-loop driver owns them. Return queue custody before completion; never
advance onto a retained pending task branch.
