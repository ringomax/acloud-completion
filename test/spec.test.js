import { test } from "node:test";
import assert from "node:assert/strict";
import spec from "../acloud.js";
import catalog from "../catalog.json" with { type: "json" };

function at(...words) {
  return words.reduce((node, name) => {
    const child = node.subcommands?.find(child => child.name === name);
    assert.ok(child, `Missing ${name}`);
    return child;
  }, spec);
}

test("every documented command has a matching completion path", () => {
  assert.ok(catalog.length >= 119);
  for (const entry of catalog) at(...entry.command.split(" ").slice(1));
});

test("database proxy accepts its database, branch and connection flags", () => {
  const node = at("db", "proxy");
  assert.equal(node.args[0].name, "DATABASE");
  assert.equal(node.options.find(o => o.name === "--branch").args.name, "BRANCH");
  assert.equal(node.options.find(o => o.name === "--port").args.name, "PORT");
  assert.equal(node.options.find(o => o.name === "--show-credentials").args, undefined);
});

test("nested application commands preserve enums and repeatable options", () => {
  const node = at("server", "applications", "create");
  assert.deepEqual(node.options.find(o => o.name === "--publishing-mode").args.suggestions, ["direct", "headless"]);
  assert.equal(node.options.find(o => o.name === "--application-path").isRepeatable, true);
  assert.equal(node.options.find(o => o.name === "--public-url").args.name, "URL");
  at("server", "applications", "publication", "advance");
  at("lb", "services", "path-rules", "switch-backend");
});

test("JSON output and project flags apply to nested commands", () => {
  assert.deepEqual(spec.options.find(o => o.name === "--format").args.suggestions, ["table", "json"]);
  assert.ok(spec.options.find(o => o.name === "--project").isPersistent);
  assert.deepEqual(at("config", "get", "project").args, undefined);
  assert.deepEqual(at("db", "branches", "list").options.find(o => o.name === "--format").args.suggestions, ["json"]);
});

test("completion contains no executable generators or private resource values", () => {
  const serialized = JSON.stringify(spec);
  assert.doesNotMatch(serialized, /"(?:generators|script|custom|postProcess)"\s*:/);
  assert.doesNotMatch(serialized, /\/Users\/|github_pat_|ghp_|BEGIN .*PRIVATE KEY/);
});
