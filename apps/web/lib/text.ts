// Detect Urdu/Arabic script so those messages render right-to-left.
// Roman Urdu (Latin letters) stays left-to-right, which is correct.
const RTL_RE = /[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]/;

export function dirOf(text: string): "rtl" | "ltr" {
  return RTL_RE.test(text) ? "rtl" : "ltr";
}
