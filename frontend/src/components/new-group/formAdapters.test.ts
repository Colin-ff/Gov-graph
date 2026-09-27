import { describe, expect, it } from "vitest";

import { applyForm, defaultMembers } from "./formAdapters";
import type { TorFormPayload } from "../../types/governance";

describe("applyForm with a sparse partial (autofill) payload", () => {
  it("populates only the fields present, leaving everything else blank", () => {
    const state = applyForm({
      group_name: "Academic Board",
      purpose: "Set academic policy.",
    });

    expect(state.groupName).toBe("Academic Board");
    expect(state.purpose).toBe("Set academic policy.");

    // Nothing else was in the payload, so every other field falls back to its
    // blank default -- this is the contract autofill relies on: a field the
    // LLM couldn't find in the document is simply absent from the payload,
    // and applyForm() (already built for partial drafts) renders it blank.
    expect(state.entityType).toBe("");
    expect(state.responsibility).toBe("");
    expect(state.reportsTo).toEqual([]);
    expect(state.meetingFreq).toBe("");
    expect(state.meetingDur).toBe("");
    expect(state.resources).toEqual([]);
    expect(state.validFrom).toBe("");
    expect(state.validTo).toBe("");
    expect(state.members).toEqual(defaultMembers());
  });

  it("applies a partially-specified member without inventing the missing fields", () => {
    // TorFormPayload.members is typed as full TorMember[], but a draft/autofill
    // payload legitimately carries partial members at runtime (drafts skip
    // validation entirely) -- the same gap `applyForm`'s own JSDoc calls out.
    const partialForm = {
      members: [{ first_name: "Ashley", last_name: "Clay", email: "a.clay@unsw.edu.au" }],
    } as Partial<TorFormPayload>;
    const state = applyForm(partialForm);

    expect(state.members).toHaveLength(1);
    const [member] = state.members;
    expect(member.name).toBe("Ashley Clay");
    expect(member.email).toBe("a.clay@unsw.edu.au");
    // zID/gender/representation/roles weren't in the extracted data.
    expect(member.zId).toBe("");
    expect(member.gender).toBe("");
    expect(member.representation).toBe("");
    expect(member.roles).toEqual([]);
  });

  it("treats an empty object the same as an untouched draft", () => {
    expect(applyForm({})).toEqual(applyForm({}));
    expect(applyForm({}).members).toEqual(defaultMembers());
  });
});
