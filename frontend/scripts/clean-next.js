const fs = require("fs");
const path = require("path");

const buildDir = path.join(__dirname, "..", ".next");

try {
  fs.rmSync(buildDir, { recursive: true, force: true });
  console.log("Cleaned .next build output");
} catch (error) {
  console.error("Failed to clean .next build output");
  console.error(error);
  process.exit(1);
}
