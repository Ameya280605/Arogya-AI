export function load(url, context, nextLoad) {
  if (url.endsWith(".css") || url.endsWith(".module.css")) {
    return {
      format: "module",
      shortCircuit: true,
      source: `
        const proxy = new Proxy({}, {
          get(_target, prop) {
            return typeof prop === "string" ? prop : "";
          }
        });
        export default proxy;
      `,
    };
  }
  return nextLoad(url, context);
}
