import { useQuery } from "@tanstack/react-query";
import { registryApi } from "@/api/registry";
import { FullPageSpinner } from "@/components/ui/Spinner";
import Card, { CardBody } from "@/components/ui/Card";
import Table from "@/components/ui/Table";
import Badge from "@/components/ui/Badge";
import type { AgentCapabilityOut } from "@/api/types";

/**
 * Read-only view of agents/registry.py (v5) — a declarative capability
 * listing (what each agent reads/writes, its risk/autonomy tags), for
 * explainability. NOT a policy engine — see that module's docstring.
 */
export default function AgentRegistryPage() {
  const query = useQuery({ queryKey: ["agent-registry"], queryFn: registryApi.list });

  if (query.isLoading) return <FullPageSpinner />;
  const agents = query.data ?? [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-800">Agent Registry</h1>
        <p className="text-sm text-slate-500">
          What every agent in this system reads, writes, and its governance tags — a declarative capability
          listing, not a runtime-enforced permission sandbox.
        </p>
      </div>

      <Card>
        <CardBody>
          <Table<AgentCapabilityOut>
            rows={agents}
            rowKey={(a) => a.name}
            columns={[
              { header: "Agent", render: (a) => <span className="font-medium text-slate-800">{a.name}</span> },
              { header: "Module", render: (a) => <code className="text-xs text-slate-500">{a.module}</code> },
              { header: "Description", render: (a) => <span className="text-slate-600">{a.description}</span> },
              {
                header: "Reads",
                render: (a) => (
                  <div className="flex flex-wrap gap-1">
                    {a.reads.map((r) => (
                      <Badge key={r} tone="info">
                        {r}
                      </Badge>
                    ))}
                  </div>
                ),
              },
              {
                header: "Writes",
                render: (a) => (
                  <div className="flex flex-wrap gap-1">
                    {a.writes.map((w) => (
                      <Badge key={w} tone="brand">
                        {w}
                      </Badge>
                    ))}
                  </div>
                ),
              },
              { header: "Risk", render: (a) => (a.risk === "—" ? a.risk : <Badge tone="warning">{a.risk}</Badge>) },
              {
                header: "Autonomy",
                render: (a) => (a.autonomy === "—" ? a.autonomy : <Badge tone="neutral">{a.autonomy}</Badge>),
              },
            ]}
          />
        </CardBody>
      </Card>
    </div>
  );
}
