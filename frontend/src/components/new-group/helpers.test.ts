import { describe, expect, it } from "vitest";
import {
  joinName,
  representationFlags,
  representationFromApi,
  representationFromFlags,
  splitName,
} from "./types";

describe("splitName", () => {
  it("splits at the first space", () => {
    expect(splitName("Anne Simmons")).toEqual({ first_name: "Anne", last_name: "Simmons" });
  });

  it("keeps everything after the first space as the last name", () => {
    expect(splitName("Mary Anne van der Berg")).toEqual({
      first_name: "Mary",
      last_name: "Anne van der Berg",
    });
  });

  it("returns an empty last name for a single word", () => {
    expect(splitName("Cher")).toEqual({ first_name: "Cher", last_name: "" });
  });

  it("collapses internal whitespace before splitting", () => {
    expect(splitName("Anne   Simmons")).toEqual({ first_name: "Anne", last_name: "Simmons" });
  });
});

describe("joinName", () => {
  it("joins first and last with a space", () => {
    expect(joinName("Anne", "Simmons")).toBe("Anne Simmons");
  });

  it("handles a missing last name", () => {
    expect(joinName("Cher", "")).toBe("Cher");
    expect(joinName("Cher", null)).toBe("Cher");
  });

  it("handles both missing", () => {
    expect(joinName(null, null)).toBe("");
  });
});

describe("representationFlags", () => {
  it('maps "staff" to is_faculty (the API term)', () => {
    expect(representationFlags("staff")).toEqual({
      is_student: false,
      is_faculty: true,
      is_external: false,
    });
  });

  it('maps "student" correctly', () => {
    expect(representationFlags("student").is_student).toBe(true);
  });

  it('maps "external" correctly', () => {
    expect(representationFlags("external").is_external).toBe(true);
  });
});

describe("representationFromFlags", () => {
  it('returns "staff" when is_faculty is set', () => {
    expect(representationFromFlags({ is_faculty: true })).toBe("staff");
  });

  it('returns "student" when is_student is set', () => {
    expect(representationFromFlags({ is_student: true })).toBe("student");
  });

  it('returns "" when nothing is set (draft not yet filled)', () => {
    expect(representationFromFlags({})).toBe("");
  });
});

describe("representationFromApi", () => {
  it('translates "faculty" to "staff"', () => {
    expect(representationFromApi("faculty")).toBe("staff");
  });

  it("passes student and external through unchanged", () => {
    expect(representationFromApi("student")).toBe("student");
    expect(representationFromApi("external")).toBe("external");
  });

  it('returns "" for unknown or missing values', () => {
    expect(representationFromApi(undefined)).toBe("");
    expect(representationFromApi("unknown")).toBe("");
  });
});
