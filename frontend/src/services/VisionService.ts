export type Detection = { track_id: number; class: string; confidence: number; bbox: number[] };
export class VisionService { constructor(private readonly baseUrl = "http://127.0.0.1:8000") {} async detect(file: Blob): Promise<Detection[]> { const body = new FormData(); body.append("file", file); const response = await fetch(`${this.baseUrl}/detect`, { method: "POST", body }); if (!response.ok) throw new Error(`Detection failed: ${response.status}`); return (await response.json()).detections; } }

