const url = "https://google.serper.dev/trends";

async function run() {
    const apiKey = process.env.SERPER_API_KEY;
    if (!apiKey) {
        throw new Error("SERPER_API_KEY is not set. Export it or load it from .env first.");
    }

    const response = await fetch(url, {
        method: "POST",
        headers: {
            "X-API-KEY": apiKey,
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            keywords: ["Polka Dots", "Lace Skirt", "Jelly Flats", "Capris", "Brut Denim"],
        }),
    });

    if (!response.ok) {
        const body = await response.text();
        throw new Error(`Serper request failed (${response.status}): ${body}`);
    }

    const data = await response.json();
    console.log(JSON.stringify(data, null, 2));
}

run().catch((err) => {
    console.error(err.message);
    process.exit(1);
});