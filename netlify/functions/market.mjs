const API = "https://api.coinbase.com/api/v3/brokerage/market";
const IDS = ["BTC-PERP-INTX", "ETH-PERP-INTX", "SOL-PERP-INTX"];

async function get(path) {
  const response = await fetch(`${API}${path}`, { headers: { "cache-control": "no-cache", "user-agent": "whale-desk-paper/0.1" } });
  if (!response.ok) throw new Error(`Coinbase ${response.status}`);
  return response.json();
}

export default async () => {
  try {
    const [productsPayload, candlesPayload] = await Promise.all([
      get(`/products?product_type=FUTURE&contract_expiry_type=PERPETUAL&limit=250`),
      get(`/products/BTC-PERP-INTX/candles?granularity=FIVE_MINUTE&limit=120&start=${Math.floor(Date.now()/1000)-36000}&end=${Math.floor(Date.now()/1000)}`),
    ]);
    const products = productsPayload.products.filter(p => IDS.includes(p.product_id)).map(p => {
      const future = p.future_product_details || {}, perp = future.perpetual_details || {};
      return { product_id:p.product_id, display_name:p.display_name, price:Number(p.price||p.mid_market_price||0), funding_rate:Number(perp.funding_rate||future.funding_rate||0), open_interest:Number(perp.open_interest||future.open_interest||0) };
    });
    const candles = (candlesPayload.candles || []).sort((a,b)=>Number(a.start)-Number(b.start));
    return new Response(JSON.stringify({ products, candles, as_of:new Date().toISOString() }), { status:200, headers:{ "content-type":"application/json", "cache-control":"public,max-age=30" } });
  } catch (error) {
    return new Response(JSON.stringify({ error:String(error.message||error) }), { status:502, headers:{ "content-type":"application/json" } });
  }
};
