// workbox-config.js (para injectManifest)
module.exports = {
  globDirectory: "build/web",
  globPatterns: [
    "**/*.{html,js,css,png,svg,json,webp,woff2}"
  ],
  swSrc: "src-sw.js",          // tu SW de origen con la lógica custom
  swDest: "build/web/sw.js"    // se generará aquí
};
