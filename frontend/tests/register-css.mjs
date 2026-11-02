import { createRequire, register } from "node:module";
import { pathToFileURL } from "node:url";

register("./css-loader.mjs", pathToFileURL("./tests/"));

const require = createRequire(import.meta.url);
require.extensions[".css"] = (module) => {
  module.exports = {
    __esModule: true,
    default: new Proxy({}, {
      get(_target, property) {
        return typeof property === "string" ? property : "";
      },
    }),
  };
};
