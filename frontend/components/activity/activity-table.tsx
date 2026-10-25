"use client";

import Link from "next/link";
import type { ActivityEvent } from "@/lib/types";
import { DecisionBadge } from "@/components/shell/decision";

export function ActivityTable({ events }: { events: ActivityEvent[] }) {
  return (
    <div className="scroll-x border-y border-hairline">
      <table className="w-full min-w-[900px] border-collapse text-left text-xs">
        <thead className="text-mute"><tr>{["Time", "Agent", "Action", "Tool", "Decision", "Latency", "Trace ID"].map((h) => <th key={h} className="border-b border-hairline px-3 py-3 font-normal">{h}</th>)}</tr></thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.id} className="border-b border-hairline last:border-b-0">
              <td className="px-3 py-4 text-mute">{event.time}</td>
              <td className="px-3 py-4">{event.agent}</td>
              <td className="px-3 py-4">{event.action}</td>
              <td className="px-3 py-4 font-bold"><Link className="focus-ring underline underline-offset-4" href={`/activity/${event.id}`}>{event.tool}</Link></td>
              <td className="px-3 py-4"><DecisionBadge decision={event.decision} /></td>
              <td className="px-3 py-4">{event.latencyMs}ms</td>
              <td className="px-3 py-4 text-mute">{event.traceId}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
