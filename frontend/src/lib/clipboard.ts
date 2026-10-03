/**
 * Copies text that may still be loading. The clipboard write starts synchronously, inside
 * the click: Safari drops the click's user activation across a network await and would
 * reject a later writeText. ClipboardItem accepts a promise for exactly this case.
 */
export async function copyText(text: Promise<string>): Promise<void> {
  if (typeof ClipboardItem !== "undefined" && typeof navigator.clipboard.write === "function") {
    const blob = text.then((value) => new Blob([value], { type: "text/plain" }));
    await navigator.clipboard.write([new ClipboardItem({ "text/plain": blob })]);
    return;
  }
  await navigator.clipboard.writeText(await text);
}
