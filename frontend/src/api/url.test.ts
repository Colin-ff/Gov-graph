import { describe, expect, it } from "vitest";
import { normaliseUrl } from "./url";

describe("normaliseUrl", () => {
  it("returns an empty string unchanged", () => {
    expect(normaliseUrl("")).toBe("");
    expect(normaliseUrl("   ")).toBe("");
  });

  it("prepends https:// when no scheme is present", () => {
    expect(normaliseUrl("www.unsw.edu.au/tor")).toBe("https://www.unsw.edu.au/tor");
    expect(normaliseUrl("sharepoint.unsw.edu.au")).toBe("https://sharepoint.unsw.edu.au");
  });

  it("leaves an existing https:// scheme alone", () => {
    const url = "https://www.unsw.edu.au/tor";
    expect(normaliseUrl(url)).toBe(url);
  });

  it("leaves an existing http:// scheme alone", () => {
    const url = "http://internal.unsw.edu.au";
    expect(normaliseUrl(url)).toBe(url);
  });

  it("does NOT prefix javascript: — opaque schemes must reach the backend's allowlist", () => {
    // Adding https:// would launder a javascript: payload into a URL that passes
    // a naive scheme check. The backend's allowlist is the right place to reject it.
    const url = "javascript:alert(1)";
    expect(normaliseUrl(url)).toBe(url);
  });

  it("does NOT prefix data: URIs", () => {
    const url = "data:text/html,<h1>hi</h1>";
    expect(normaliseUrl(url)).toBe(url);
  });

  it("handles a host:port URL without wrongly treating the colon as a scheme", () => {
    expect(normaliseUrl("example.com:8080/path")).toBe("https://example.com:8080/path");
  });

  it("trims leading and trailing whitespace before checking", () => {
    expect(normaliseUrl("  www.example.com  ")).toBe("https://www.example.com");
  });
});
