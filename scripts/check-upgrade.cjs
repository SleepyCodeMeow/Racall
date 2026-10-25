// Installation is guarded inside the scenario and only allowed on a fresh hosted runner.
require('./upgrade/scenario.cjs')
  .runUpgrade()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
