const { ethers } = require("hardhat");

async function main() {
  console.log("=".repeat(80));
  console.log("ESCROW SMART CONTRACT DEPLOYMENT & INTERACTION SCRIPT");
  console.log("=".repeat(80));

  const [deployer, buyer, seller, arbiter] = await ethers.getSigners();
  const depositAmount = ethers.parseEther("2.0");

  console.log(`Deployer Address: ${deployer.address}`);
  console.log(`Buyer Address:    ${buyer.address}`);
  console.log(`Seller Address:   ${seller.address}`);
  console.log(`Arbiter Address:  ${arbiter.address}`);
  console.log(`Escrow Deposit:   ${ethers.formatEther(depositAmount)} ETH\n`);

  // 1. Deploy Contract
  console.log("--- 1. DEPLOYING ESCROW CONTRACT ---");
  const Escrow = await ethers.getContractFactory("Escrow");
  const escrow = await Escrow.deploy(buyer.address, seller.address, arbiter.address, depositAmount);
  await escrow.waitForDeployment();

  const contractAddress = await escrow.getAddress();
  const deploymentTx = escrow.deploymentTransaction();
  const deployReceipt = await deploymentTx.wait();

  console.log(`Deployed Contract Address: ${contractAddress}`);
  console.log(`Deployment Tx Hash:        ${deployReceipt.hash}`);
  console.log(`Deployment Gas Used:       ${deployReceipt.gasUsed.toString()}`);
  console.log(`Contract Initial State:    ${await escrow.currentState()} (Created)`);
  console.log(`Contract Initial Balance:  ${ethers.formatEther(await ethers.provider.getBalance(contractAddress))} ETH\n`);

  // 2. Buyer Deposits ETH
  console.log("--- 2. BUYER DEPOSITS 2.0 ETH ---");
  const depTx = await escrow.connect(buyer).deposit({ value: depositAmount });
  const depReceipt = await depTx.wait();
  console.log(`Deposit Tx Hash:   ${depReceipt.hash}`);
  console.log(`Deposit Gas Used:  ${depReceipt.gasUsed.toString()}`);
  console.log(`Current State:     ${await escrow.currentState()} (Funded)`);
  console.log(`Contract Balance:  ${ethers.formatEther(await ethers.provider.getBalance(contractAddress))} ETH`);
  console.log(`Solvency Verified: ${await escrow.verifySolvency()}\n`);

  // 3. Buyer Releases Payment
  console.log("--- 3. BUYER RELEASES PAYMENT TO SELLER ---");
  const relTx = await escrow.connect(buyer).releasePayment();
  const relReceipt = await relTx.wait();
  console.log(`Release Tx Hash:   ${relReceipt.hash}`);
  console.log(`Release Gas Used:  ${relReceipt.gasUsed.toString()}`);
  console.log(`Current State:     ${await escrow.currentState()} (Released)`);
  console.log(`Seller Pending:    ${ethers.formatEther(await escrow.withdrawableFunds(seller.address))} ETH`);
  console.log(`Solvency Verified: ${await escrow.verifySolvency()}\n`);

  // 4. Seller Withdraws Funds (Pull Payment)
  console.log("--- 4. SELLER EXECUTES PULL PAYMENT WITHDRAWAL ---");
  const sellerBalBefore = await ethers.provider.getBalance(seller.address);
  const wTx = await escrow.connect(seller).withdraw();
  const wReceipt = await wTx.wait();
  const sellerGas = wReceipt.gasUsed * wReceipt.gasPrice;
  const sellerBalAfter = await ethers.provider.getBalance(seller.address);

  console.log(`Withdraw Tx Hash:  ${wReceipt.hash}`);
  console.log(`Withdraw Gas Used: ${wReceipt.gasUsed.toString()}`);
  console.log(`Seller Delta ETH:  +${ethers.formatEther(sellerBalAfter - sellerBalBefore + sellerGas)} ETH (before gas)`);
  console.log(`Contract Final Bal:${ethers.formatEther(await ethers.provider.getBalance(contractAddress))} ETH`);
  console.log(`Contract Total Liab:${ethers.formatEther(await escrow.totalLiabilities())} ETH`);
  console.log(`Solvency Verified: ${await escrow.verifySolvency()}\n`);

  // 5. Gas Summary Table
  console.log("=".repeat(80));
  console.log("GAS REPORT SUMMARY");
  console.log("=".repeat(80));
  console.log(`Operation                 | Gas Used`);
  console.log(`--------------------------|------------------`);
  console.log(`Contract Deployment       | ${deployReceipt.gasUsed.toString()}`);
  console.log(`Buyer Deposit (2.0 ETH)   | ${depReceipt.gasUsed.toString()}`);
  console.log(`Buyer Release Payment     | ${relReceipt.gasUsed.toString()}`);
  console.log(`Seller Pull Withdrawal    | ${wReceipt.gasUsed.toString()}`);
  console.log("=".repeat(80));
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });

