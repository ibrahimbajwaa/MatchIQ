// Runs the mock API:  npm run mock   (then  npm run dev  in another terminal)
import { createServer } from "node:http";
import { createApi, loadDataset } from "./api.mjs";

const handle = createApi(loadDataset());
const port = Number(process.env.PORT ?? 8787);

createServer((req, res) => {
  const { status, body } = handle(req.url ?? "/");
  res.writeHead(status, {
    "content-type": status === 200 ? "application/json" : "application/problem+json",
    "access-control-allow-origin": "*",
    "cache-control": "no-store",
  });
  res.end(JSON.stringify(body));
}).listen(port, () => console.log(`MatchIQ mock API on http://localhost:${port}`));
