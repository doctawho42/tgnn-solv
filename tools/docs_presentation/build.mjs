import { build } from "esbuild";
import { mkdir } from "node:fs/promises";
import { execFile } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const docsRoot = path.resolve(__dirname, "../../docs/assets");
const execFileAsync = promisify(execFile);

async function generatePresentationData() {
  const scriptPath = path.join(__dirname, "generate_presentation_data.py");
  const candidates = [process.env.PYTHON, "python", "python3"].filter(Boolean);
  let lastError = null;

  for (const candidate of candidates) {
    try {
      await execFileAsync(candidate, [scriptPath], {
        cwd: path.resolve(__dirname, "../.."),
        env: process.env,
      });
      return;
    } catch (error) {
      lastError = error;
    }
  }

  if (lastError) {
    throw lastError;
  }
}

await mkdir(path.join(docsRoot, "javascripts"), { recursive: true });
await mkdir(path.join(docsRoot, "stylesheets"), { recursive: true });
await mkdir(path.join(docsRoot, "data"), { recursive: true });

await generatePresentationData();

await build({
  entryPoints: [path.join(__dirname, "src/main.jsx")],
  bundle: true,
  format: "iife",
  minify: false,
  platform: "browser",
  jsx: "automatic",
  loader: {
    ".js": "jsx",
  },
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  outfile: path.join(docsRoot, "javascripts/tgnn-presentation.bundle.js"),
});

await build({
  entryPoints: [path.join(__dirname, "src/presentation.css")],
  bundle: true,
  minify: false,
  outfile: path.join(docsRoot, "stylesheets/tgnn-presentation.css"),
});
