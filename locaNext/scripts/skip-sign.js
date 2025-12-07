// Custom sign function that does nothing
// Workaround for electron-builder NSIS signing bug
// See: https://github.com/electron-userland/electron-builder/issues/7942

exports.default = async function(configuration) {
  // Do nothing - skip signing
  console.log("  • Skipping code signing (no certificate configured)");
};
