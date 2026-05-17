import { streamText } from "ai";

export const maxDuration = 60;

export async function POST(req: Request) {
  const { symbol, technical, sentiment, news } = await req.json();

  const prompt = `Sen bir kıdemli swing-trading analistisin. Aşağıdaki çoklu sinyalleri değerlendir ve 5-15 gün vadeli AL/SAT/BEKLE kararı ver.

Sembol: ${symbol}

TEKNİK SİNYALLER:
${JSON.stringify(technical, null, 2)}

SENTIMENT (FinBERT):
${JSON.stringify(sentiment, null, 2)}

SON HABERLER (özet):
${(news ?? []).map((n: { headline: string }) => `- ${n.headline}`).join("\n")}

Yanıt formatı:
1) Karar: BUY / SELL / HOLD
2) Güven (0-1):
3) Beklenen tutma süresi (gün):
4) Gerekçe (3-5 cümle, neden bu yönde olduğunu açıkla):
5) Risk faktörleri:
6) Stop-loss / target önerisi:`;

  const result = streamText({
    model: "anthropic/claude-sonnet-4-6",
    prompt,
    temperature: 0.3,
  });

  return result.toTextStreamResponse();
}
