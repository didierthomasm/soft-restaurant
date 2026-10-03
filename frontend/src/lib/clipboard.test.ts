import { afterEach, describe, expect, it, vi } from "vitest";

import { copyText } from "./clipboard";

class FakeClipboardItem {
  constructor(readonly items: Record<string, Promise<Blob>>) {}
}

describe("copyText", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("starts the clipboard write before the text is ready (Safari user activation)", async () => {
    vi.stubGlobal("ClipboardItem", FakeClipboardItem);
    const write = vi.fn(async () => undefined);
    vi.stubGlobal("navigator", { clipboard: { write, writeText: vi.fn() } });
    let resolve: (value: string) => void = () => undefined;
    const text = new Promise<string>((r) => {
      resolve = r;
    });

    const done = copyText(text);
    expect(write).toHaveBeenCalledTimes(1);

    resolve("A\tB");
    await done;
    const [item] = (write.mock.calls[0] as unknown as [FakeClipboardItem[]])[0];
    await expect((await item.items["text/plain"]).text()).resolves.toBe("A\tB");
  });

  it("falls back to writeText without ClipboardItem", async () => {
    vi.stubGlobal("ClipboardItem", undefined);
    const writeText = vi.fn(async () => undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    await copyText(Promise.resolve("hola"));
    expect(writeText).toHaveBeenCalledWith("hola");
  });
});
