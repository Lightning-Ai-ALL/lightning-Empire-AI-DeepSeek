const EmpireVault = artifacts.require("EmpireVault");

module.exports = async function (deployer, network, accounts) {
    const usdcAddress = network === 'mainnet' 
        ? '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'  // Ethereum mainnet USDC
        : '0x07865c6E87B9F70255377e024ace6630C1Eaa37F'; // Goerli testnet USDC
    await deployer.deploy(EmpireVault, usdcAddress);
};
