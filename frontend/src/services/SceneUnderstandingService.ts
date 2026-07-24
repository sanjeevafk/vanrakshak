export class SceneUnderstandingService {
  constructor(private readonly baseUrl = "http://127.0.0.1:8000") {}
  async understand(imageBase64: string) {
    const response = await fetch(`${this.baseUrl}/scene-understanding`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ image: imageBase64 })
    });
    if (!response.ok) throw new Error(`Scene understanding failed: ${response.status}`);
    return response.json();
  }
}

