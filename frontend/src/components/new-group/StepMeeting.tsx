import { FormField } from "./FormField";
import { normaliseUrl } from "../../api/url";
import type { ResourceEntry } from "./types";

const inp = "w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500";
const numInp = "border border-gray-300 rounded px-3 py-2 text-sm w-20 focus:outline-none focus:border-blue-500";

export function StepMeeting({
  meetingFreq, setMeetingFreq,
  meetingDur, setMeetingDur,
  resources, setResources,
}: {
  meetingFreq: string; setMeetingFreq: (v: string) => void;
  meetingDur: string; setMeetingDur: (v: string) => void;
  resources: ResourceEntry[]; setResources: (v: ResourceEntry[]) => void;
}) {
  function updateResource(i: number, patch: Partial<ResourceEntry>) {
    const copy = [...resources];
    copy[i] = { ...copy[i], ...patch };
    setResources(copy);
  }

  return (
    <div className="space-y-6">
      <div className="flex gap-8">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Meeting frequency</label>
          <div className="flex items-center gap-2">
            <input type="number" min="0" className={numInp} value={meetingFreq} onChange={e => setMeetingFreq(e.target.value)} placeholder="0" />
            <span className="text-sm text-gray-500">times / yr</span>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Meeting duration</label>
          <div className="flex items-center gap-2">
            <input type="number" min="0" step="0.5" className={numInp} value={meetingDur} onChange={e => setMeetingDur(e.target.value)} placeholder="0" />
            <span className="text-sm text-gray-500">h / meeting</span>
          </div>
        </div>
      </div>

      <div>
        <p className="text-sm font-medium text-gray-700 mb-3">Resources</p>
        {resources.map((r, i) => (
          <div key={i} className="flex gap-3 items-end mb-3">
            <div className="flex-1">
              <FormField label="Title" required small>
                <input className={inp} value={r.title} onChange={e => updateResource(i, { title: e.target.value })} />
              </FormField>
            </div>
            <div className="flex-1">
              {/* "URL" reads as jargon to the governance staff filling this in. */}
              <FormField label="Source link" small>
                <input
                  className={inp}
                  type="text"
                  value={r.url}
                  placeholder="www.unsw.edu.au/..."
                  onChange={e => updateResource(i, { url: e.target.value })}
                  // Fill in the scheme once they move on, so what they see here
                  // matches what gets stored.
                  onBlur={e => updateResource(i, { url: normaliseUrl(e.target.value) })}
                />
              </FormField>
            </div>
            <button
              onClick={() => setResources(resources.filter((_, j) => j !== i))}
              className="text-gray-400 hover:text-red-500 text-xl leading-none pb-2"
            >
              ×
            </button>
          </div>
        ))}
        <button onClick={() => setResources([...resources, { title: "", url: "" }])} className="text-sm text-blue-600 hover:underline">
          + Add resource
        </button>
      </div>
    </div>
  );
}
