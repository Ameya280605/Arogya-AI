import { register } from "node:module";
import { pathToFileURL } from "node:url";

register("./css-loader.mjs", pathToFileURL("./tests/"));
