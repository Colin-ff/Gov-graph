import { beforeEach, describe, expect, it, vi } from "vitest";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
let isAxiosError = false;

vi.mock("axios", () => ({
  default: {
    create: () => ({
      post,
      get,
      put: vi.fn(),
      delete: vi.fn(),
      interceptors: { request: { use: vi.fn() } },
    }),
    isAxiosError: () => isAxiosError,
  },
}));

import { autofillTor, fetchGraph, apiErrorMessages } from "./client";

beforeEach(() => {
  get.mockReset();
  post.mockReset();
  isAxiosError = false;
});

describe("autofillTor", () => {

  it("posts the file as multipart form data and returns the sparse form", async () => {
    const sparseForm = { group_name: "Academic Board" };
    post.mockResolvedValue({ data: { form_json_data: sparseForm } });

    const file = new File(["document contents"], "tor.docx");
    const result = await autofillTor(file);

    expect(post).toHaveBeenCalledTimes(1);
    const [url, body] = post.mock.calls[0];
    expect(url).toBe("/tor/autofill");
    expect(body).toBeInstanceOf(FormData);
    expect((body as FormData).get("file")).toBe(file);
    expect(result).toEqual(sparseForm);
  });
});

describe("fetchGraph", () => {
  it("calls GET /graph and returns nodes and relations", async () => {
    const payload = { nodes: [{ uuid: "abc", group_name: "Council" }], relations: [] };
    get.mockResolvedValue({ data: payload });

    const result = await fetchGraph();

    expect(get).toHaveBeenCalledWith("/graph");
    expect(result).toEqual(payload);
  });
});

describe("apiErrorMessages", () => {
  it("returns a generic message for non-axios errors", () => {
    expect(apiErrorMessages(new Error("boom"))).toEqual([
      "Something went wrong. Please try again.",
    ]);
  });

  it("extracts per-field details from a 400 response", () => {
    isAxiosError = true;
    const err = {
      response: { status: 400, data: { details: { purpose: "required", group_name: "too short" } } },
    };
    const msgs = apiErrorMessages(err);
    expect(msgs).toContain("purpose: required");
    expect(msgs).toContain("group_name: too short");
  });

  it("returns a login prompt on 401", () => {
    isAxiosError = true;
    const err = { response: { status: 401, data: {} } };
    const [msg] = apiErrorMessages(err);
    expect(msg).toMatch(/log in/i);
  });

  it("falls back to the top-level error string", () => {
    isAxiosError = true;
    const err = { response: { status: 422, data: { error: "Validation failed" } } };
    expect(apiErrorMessages(err)).toEqual(["Validation failed"]);
  });
});
