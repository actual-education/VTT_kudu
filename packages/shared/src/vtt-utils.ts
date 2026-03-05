import { VttCue } from "./types";

export function formatVttTimestamp(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const ms = Math.round((seconds % 1) * 1000);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}.${String(ms).padStart(3, "0")}`;
}

export function parseVttTimestamp(ts: string): number {
  const parts = ts.split(":");
  if (parts.length === 3) {
    const [h, m, rest] = parts;
    const [s, ms] = rest.split(".");
    return parseInt(h) * 3600 + parseInt(m) * 60 + parseInt(s) + (ms ? parseInt(ms.padEnd(3, "0")) / 1000 : 0);
  }
  if (parts.length === 2) {
    const [m, rest] = parts;
    const [s, ms] = rest.split(".");
    return parseInt(m) * 60 + parseInt(s) + (ms ? parseInt(ms.padEnd(3, "0")) / 1000 : 0);
  }
  return 0;
}

export function generateVtt(cues: VttCue[]): string {
  let vtt = "WEBVTT\n\n";
  cues.forEach((cue, i) => {
    if (cue.id) {
      vtt += `${cue.id}\n`;
    }
    vtt += `${formatVttTimestamp(cue.startTime)} --> ${formatVttTimestamp(cue.endTime)}\n`;
    vtt += `${cue.text}\n\n`;
  });
  return vtt;
}

export function parseVtt(content: string): VttCue[] {
  const cues: VttCue[] = [];
  const lines = content.split("\n");
  let i = 0;

  // Skip WEBVTT header
  while (i < lines.length && !lines[i].includes("-->")) {
    i++;
  }

  while (i < lines.length) {
    const line = lines[i].trim();
    if (line.includes("-->")) {
      const [startStr, endStr] = line.split("-->").map((s) => s.trim());
      const startTime = parseVttTimestamp(startStr);
      const endTime = parseVttTimestamp(endStr);
      i++;
      const textLines: string[] = [];
      while (i < lines.length && lines[i].trim() !== "") {
        textLines.push(lines[i].trim());
        i++;
      }
      cues.push({ startTime, endTime, text: textLines.join("\n") });
    }
    i++;
  }

  return cues;
}
