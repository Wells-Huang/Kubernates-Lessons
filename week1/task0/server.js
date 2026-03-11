const http = require("http");
const os = require("os");

const port = Number(process.env.PORT || 3000);

const server = http.createServer((req, res) => {
  const body = {
    message: "multi-arch javascript sample is running",
    arch: process.arch,
    platform: process.platform,
    hostname: os.hostname(),
    url: req.url,
  };

  res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(body, null, 2));
});

server.listen(port, "0.0.0.0", () => {
  console.log(`Server listening on port ${port}`);
});
