// Compila _data/<pack>.json a packs/<pack> (LevelDB para Foundry v13/v14) y empaqueta dist/module.zip
import fs from "node:fs/promises";
import { createWriteStream } from "node:fs";
import { ClassicLevel } from "classic-level";
import archiver from "archiver";

const PREFIJOS = {
  Adventure: "adventures",
  JournalEntry: "journal",
  Item: "items",
  Actor: "actors",
  RollTable: "tables",
  Macro: "macros",
};

const manifest = JSON.parse(await fs.readFile("module.json", "utf8"));

for (const pack of manifest.packs) {
  await fs.rm(pack.path, { recursive: true, force: true });
  const db = new ClassicLevel(pack.path, { valueEncoding: "json" });
  const docs = JSON.parse(await fs.readFile(`_data/${pack.name}.json`, "utf8"));
  const pref = PREFIJOS[pack.type] || "items";

  for (const raw of docs) {
    const d = structuredClone(raw);

    if (pack.type === "JournalEntry" && Array.isArray(d.pages)) {
      const pageIds = [];
      for (const p of d.pages) {
        pageIds.push(p._id);
        await db.put(`!journal.pages!${d._id}.${p._id}`, p);
      }
      d.pages = pageIds;
    } else if (pack.type === "Actor" && Array.isArray(d.items)) {
      const itemIds = [];
      for (const it of d.items) {
        itemIds.push(it._id);
        await db.put(`!actors.items!${d._id}.${it._id}`, it);
      }
      d.items = itemIds;
      d.effects ??= [];
    } else if (pack.type === "RollTable" && Array.isArray(d.results)) {
      const resIds = [];
      for (const r of d.results) {
        resIds.push(r._id);
        await db.put(`!tables.results!${d._id}.${r._id}`, r);
      }
      d.results = resIds;
    }

    await db.put(`!${pref}!${d._id}`, d);
  }

  await db.close();
  console.log(`  [OK] Pack ${pack.name} (${pack.type}): ${docs.length} documento(s)`);
}

await fs.mkdir("dist", { recursive: true });
const out = createWriteStream("dist/module.zip");
const zip = archiver("zip", { zlib: { level: 9 } });
zip.pipe(out);
const done = new Promise((res, rej) => {
  out.on("close", res);
  out.on("error", rej);
  zip.on("error", rej);
});

for (const p of ["module.json", "js", "styles", "lang", "packs", "assets", "content", "LICENSE", "NOTICE.md", "README.md", "CHANGELOG.md"]) {
  try {
    const st = await fs.stat(p);
    if (st.isDirectory()) zip.directory(p, p);
    else zip.file(p, { name: p });
  } catch {
    // Opcional
  }
}

await zip.finalize();
await done;
await fs.copyFile("module.json", "dist/module.json");
console.log("  [OK] Empaquetado dist/module.zip y dist/module.json");
