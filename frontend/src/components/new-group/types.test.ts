import { describe, expect, it } from "vitest";

import {
  blankPerson,
  CHAIR_ROLE,
  dedupeDesignatedRoles,
  SECRETARIAT_ROLE,
} from "./types";

describe("dedupeDesignatedRoles", () => {
  it("strips a duplicate Chair from a later (common member) row", () => {
    // The exact bad state seen in a stored draft: a common member ended up with
    // ["Member", "Chair"] via the create-role path.
    const members = [
      blankPerson([CHAIR_ROLE, SECRETARIAT_ROLE]),
      blankPerson(["Member", CHAIR_ROLE]),
    ];

    const cleaned = dedupeDesignatedRoles(members);

    expect(cleaned[0].roles).toEqual([CHAIR_ROLE, SECRETARIAT_ROLE]);
    expect(cleaned[1].roles).toEqual(["Member"]);
  });

  it("keeps the first holder of each designated role, matched case-insensitively", () => {
    const members = [
      blankPerson([CHAIR_ROLE]),
      blankPerson([SECRETARIAT_ROLE]),
      blankPerson(["Member", "secretariat"]),
    ];

    const cleaned = dedupeDesignatedRoles(members);

    expect(cleaned[0].roles).toEqual([CHAIR_ROLE]);
    expect(cleaned[1].roles).toEqual([SECRETARIAT_ROLE]);
    expect(cleaned[2].roles).toEqual(["Member"]);
  });

  it("returns the same array reference when nothing needs changing", () => {
    const members = [
      blankPerson([CHAIR_ROLE, SECRETARIAT_ROLE]),
      blankPerson(["Member"]),
    ];

    expect(dedupeDesignatedRoles(members)).toBe(members);
  });
});
