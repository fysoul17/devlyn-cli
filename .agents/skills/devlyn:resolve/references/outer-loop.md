# Outer-loop commit boundary

A full `/devlyn:resolve` run starts only from committed owner inputs. Keep each
commit scoped: no unrelated paths or queue-item changes.

1. Before an item's first full run, commit the current queue-item delta, when
   applicable, together with its linked spec bundle. For conversational work,
   commit the agreed spec bundle before the full run.
2. When findings require an accepted verification amendment, commit only that
   linked spec-bundle amendment before rerunning the item.
3. After a terminal result, commit the current item's `[x]` or `[F]` queue
   transition before starting the next pending item.

Drain strictly serially. Bootstrap and resolve never make these owner commits;
the outer-loop driver owns them.
