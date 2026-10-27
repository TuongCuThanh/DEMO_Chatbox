function CLAUDE(prompt) {
  const apiKey = "YOUR_API_KEY_HERE"; // paste API key của bạn
  const response = UrlFetchApp.fetch("https://api.anthropic.com/v1/messages", {
    method: "post",
    headers: {
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json"
    },
    payload: JSON.stringify({
      model: "claude-sonnet-4-6",
      max_tokens: 1024,
      messages: [{ role: "user", content: prompt }]
    })
  });
  const data = JSON.parse(response.getContentText());
  return data.content[0].text;
}