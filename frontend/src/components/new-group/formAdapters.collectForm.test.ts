import { describe, expect, it } from "vitest";
import { applyForm, collectForm, FORM_VERSION } from "./formAdapters";
import { CHAIR_ROLE, SECRETARIAT_ROLE } from "./types";
import type { WizardFormState } from "./formAdapters";

function state(overrides: Partial<WizardFormState> = {}): WizardFormState {
  return {
    groupName: "Academic Board",
    entityType: "Board",
    purpose: "Academic governance.",
    responsibility: "Set policy.",
    members: [
      { uuid: null, name: "Anne Simmons", gender: "Female", email: "a@unsw.edu.au", phone: "", zId: "1234567", representation: "staff", roles: [CHAIR_ROLE] },
      { uuid: null, name: "Mark Chen",    gender: "Male",   email: "m@unsw.edu.au", phone: "", zId: "7654321", representation: "staff", roles: [SECRETARIAT_ROLE] },
    ],
    reportsTo: [],
    meetingFreq: "6",
    meetingDur: "2",
    resources: [],
    validFrom: "2024-01-01",
    validTo: "2026-01-01",
    ...overrides,
  };
}

describe("collectForm", () => {
  it("serialises top-level fields correctly", () => {
    const p = collectForm(state());
    expect(p.form_version).toBe(FORM_VERSION);
    expect(p.group_name).toBe("Academic Board");
    expect(p.responsibilities).toBe("Set policy.");
    expect(p.meeting_frequency_per_year).toBe(6);
    expect(p.meeting_duration_hour).toBe(2);
  });

  it("falls back to 0 when meeting fields are empty strings", () => {
    const p = collectForm(state({ meetingFreq: "", meetingDur: "" }));
    expect(p.meeting_frequency_per_year).toBe(0);
    expect(p.meeting_duration_hour).toBe(0);
  });

  it("splits name and prefixes zID with z for internal members", () => {
    const chair = collectForm(state()).members[0];
    expect(chair.first_name).toBe("Anne");
    expect(chair.last_name).toBe("Simmons");
    expect(chair.zID).toBe("z1234567");
    expect(chair.is_external).toBe(false);
  });

  it("sets zID to null for external members", () => {
    const s = state();
    s.members[0] = { ...s.members[0], representation: "external", zId: "" };
    const chair = collectForm(s).members[0];
    expect(chair.zID).toBeNull();
    expect(chair.is_external).toBe(true);
  });

  it("keeps everything after the first space as the last name", () => {
    const s = state();
    s.members[0].name = "Mary Anne van der Berg";
    const m = collectForm(s).members[0];
    expect(m.first_name).toBe("Mary");
    expect(m.last_name).toBe("Anne van der Berg");
  });

  it("maps an existing reporting line with its uuid", () => {
    const s = state({ reportsTo: [{ groupName: "University Council", groupUuid: "uc-1", note: "" }] });
    const rel = collectForm(s).relations[0];
    expect(rel.existing_group).toBe(true);
    if (rel.existing_group) expect(rel.group_uuid).toBe("uc-1");
  });

  it("maps a proposed (unregistered) reporting line", () => {
    const s = state({ reportsTo: [{ groupName: "New Body", groupUuid: null, note: "" }] });
    const rel = collectForm(s).relations[0];
    expect(rel.existing_group).toBe(false);
    if (!rel.existing_group) expect(rel.group_name).toBe("New Body");
  });

  it("drops blank reporting line rows", () => {
    const s = state({
      reportsTo: [
        { groupName: "", groupUuid: null, note: "" },
        { groupName: "Council", groupUuid: "x", note: "" },
      ],
    });
    expect(collectForm(s).relations).toHaveLength(1);
  });

  it("drops reference links with no title", () => {
    const s = state({
      resources: [
        { title: "ToR", url: "https://sharepoint.unsw.edu.au" },
        { title: "", url: "https://example.com" },
      ],
    });
    expect(collectForm(s).reference_links).toHaveLength(1);
  });

  it("round-trips through applyForm without data loss", () => {
    const original = state();
    const back = applyForm(collectForm(original));
    expect(back.groupName).toBe(original.groupName);
    expect(back.responsibility).toBe(original.responsibility);
    expect(back.meetingFreq).toBe(original.meetingFreq);
    expect(back.validFrom).toBe(original.validFrom);
  });
});
