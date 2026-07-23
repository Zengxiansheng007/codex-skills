# Orchestration And Fallback

The main agent owns the research question, source policy, safety boundary, synthesis, and final status.

Use background agents only when:

- the task has separable subtopics;
- subagents can work with public or approved data only;
- the main agent can verify their sources;
- the added cost and delay are justified.

Do not delegate:

- secret handling;
- final conclusions;
- legal or security acceptance;
- direct changes to code/config/docs.

Fallback modes:

| Problem | Response |
|---|---|
| No background agent | Run synchronously and record `orchestrationMode: sync` |
| One branch fails | Continue, mark branch `partial`, keep failure reason |
| All primary sources blocked | Use fallback sources and mark confidence lower |
| Deadline reached | Return `partial` with open questions |
| Safety boundary unclear | Stop and ask user |

Long work should record progress checkpoints in `search-log`.
