const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Escrow Smart Contract (Assignment 7)", function () {
  let Escrow;
  let escrow;
  let owner, buyer, seller, arbiter, attacker, otherUser;
  const depositAmount = ethers.parseEther("1.5");

  beforeEach(async function () {
    [owner, buyer, seller, arbiter, attacker, otherUser] = await ethers.getSigners();
    Escrow = await ethers.getContractFactory("Escrow");
    escrow = await Escrow.deploy(buyer.address, seller.address, arbiter.address, depositAmount);
    await escrow.waitForDeployment();
  });

  // -------------------------------------------------------------------------
  // 1. Constructor and Parameter Validations
  // -------------------------------------------------------------------------
  describe("Constructor & Initialization", function () {
    it("should initialize with correct roles, targetDeposit, and Created state", async function () {
      expect(await escrow.buyer()).to.equal(buyer.address);
      expect(await escrow.seller()).to.equal(seller.address);
      expect(await escrow.arbiter()).to.equal(arbiter.address);
      expect(await escrow.targetDeposit()).to.equal(depositAmount);
      expect(await escrow.currentState()).to.equal(0); // State.Created
      expect(await escrow.verifySolvency()).to.be.true;
    });

    it("should revert if any role is address(0)", async function () {
      const zero = ethers.ZeroAddress;
      await expect(Escrow.deploy(zero, seller.address, arbiter.address, depositAmount))
        .to.be.revertedWithCustomError(escrow, "ZeroAddressDetected");
      await expect(Escrow.deploy(buyer.address, zero, arbiter.address, depositAmount))
        .to.be.revertedWithCustomError(escrow, "ZeroAddressDetected");
      await expect(Escrow.deploy(buyer.address, seller.address, zero, depositAmount))
        .to.be.revertedWithCustomError(escrow, "ZeroAddressDetected");
    });

    it("should revert if roles overlap", async function () {
      // buyer == seller
      await expect(Escrow.deploy(buyer.address, buyer.address, arbiter.address, depositAmount))
        .to.be.revertedWithCustomError(escrow, "RoleOverlapDetected");
      // arbiter == buyer
      await expect(Escrow.deploy(buyer.address, seller.address, buyer.address, depositAmount))
        .to.be.revertedWithCustomError(escrow, "RoleOverlapDetected");
      // arbiter == seller
      await expect(Escrow.deploy(buyer.address, seller.address, seller.address, depositAmount))
        .to.be.revertedWithCustomError(escrow, "RoleOverlapDetected");
    });

    it("should revert if targetDeposit is 0", async function () {
      await expect(Escrow.deploy(buyer.address, seller.address, arbiter.address, 0))
        .to.be.revertedWithCustomError(escrow, "InvalidDepositAmount");
    });
  });

  // -------------------------------------------------------------------------
  // 2. Deposit & Funding
  // -------------------------------------------------------------------------
  describe("Deposit Workflow", function () {
    it("should permit buyer to deposit exact target amount", async function () {
      await expect(escrow.connect(buyer).deposit({ value: depositAmount }))
        .to.emit(escrow, "Funded")
        .withArgs(buyer.address, depositAmount);

      expect(await escrow.currentState()).to.equal(1); // State.Funded
      expect(await ethers.provider.getBalance(await escrow.getAddress())).to.equal(depositAmount);
    });

    it("should reject deposit from unauthorized caller", async function () {
      await expect(escrow.connect(attacker).deposit({ value: depositAmount }))
        .to.be.revertedWithCustomError(escrow, "UnauthorizedCaller")
        .withArgs(attacker.address);
    });

    it("should reject deposit with incorrect ETH value", async function () {
      const wrongAmount = ethers.parseEther("1.0");
      await expect(escrow.connect(buyer).deposit({ value: wrongAmount }))
        .to.be.revertedWithCustomError(escrow, "DepositAmountMismatch")
        .withArgs(depositAmount, wrongAmount);
    });

    it("should reject second deposit once funded", async function () {
      await escrow.connect(buyer).deposit({ value: depositAmount });
      await expect(escrow.connect(buyer).deposit({ value: depositAmount }))
        .to.be.revertedWithCustomError(escrow, "InvalidState");
    });
  });

  // -------------------------------------------------------------------------
  // 3. Normal Release Workflow
  // -------------------------------------------------------------------------
  describe("Payment Release Workflow", function () {
    beforeEach(async function () {
      await escrow.connect(buyer).deposit({ value: depositAmount });
    });

    it("should permit buyer to release payment to seller", async function () {
      await expect(escrow.connect(buyer).releasePayment())
        .to.emit(escrow, "Released")
        .withArgs(seller.address, depositAmount);

      expect(await escrow.currentState()).to.equal(2); // State.Released
      expect(await escrow.withdrawableFunds(seller.address)).to.equal(depositAmount);
      expect(await escrow.verifySolvency()).to.be.true;

      // Seller withdraws
      const balanceBefore = await ethers.provider.getBalance(seller.address);
      const tx = await escrow.connect(seller).withdraw();
      const receipt = await tx.wait();
      const gasSpent = receipt.gasUsed * receipt.gasPrice;
      const balanceAfter = await ethers.provider.getBalance(seller.address);

      expect(balanceAfter).to.equal(balanceBefore + depositAmount - gasSpent);
      expect(await escrow.withdrawableFunds(seller.address)).to.equal(0);
      expect(await escrow.verifySolvency()).to.be.true;
    });

    it("should reject payment release by seller or third party", async function () {
      await expect(escrow.connect(seller).releasePayment())
        .to.be.revertedWithCustomError(escrow, "UnauthorizedCaller");
      await expect(escrow.connect(attacker).releasePayment())
        .to.be.revertedWithCustomError(escrow, "UnauthorizedCaller");
    });

    it("should reject release after terminal state", async function () {
      await escrow.connect(buyer).releasePayment();
      await expect(escrow.connect(buyer).releasePayment())
        .to.be.revertedWithCustomError(escrow, "InvalidState");
    });
  });

  // -------------------------------------------------------------------------
  // 4. Dispute & Arbiter Resolution Workflow
  // -------------------------------------------------------------------------
  describe("Dispute and Arbiter Resolution", function () {
    beforeEach(async function () {
      await escrow.connect(buyer).deposit({ value: depositAmount });
    });

    it("should permit buyer or seller to raise a dispute", async function () {
      await expect(escrow.connect(seller).raiseDispute())
        .to.emit(escrow, "DisputeRaised")
        .withArgs(seller.address);

      expect(await escrow.currentState()).to.equal(3); // State.Disputed
    });

    it("should reject dispute raised by third party or arbiter", async function () {
      await expect(escrow.connect(attacker).raiseDispute())
        .to.be.revertedWithCustomError(escrow, "UnauthorizedCaller");
      await expect(escrow.connect(arbiter).raiseDispute())
        .to.be.revertedWithCustomError(escrow, "UnauthorizedCaller");
    });

    it("should permit arbiter to resolve dispute in favor of buyer", async function () {
      await escrow.connect(buyer).raiseDispute();

      await expect(escrow.connect(arbiter).resolveDispute(true))
        .to.emit(escrow, "Resolved")
        .withArgs(4, buyer.address, depositAmount); // State.ResolvedToBuyer = 4

      expect(await escrow.currentState()).to.equal(4);
      expect(await escrow.withdrawableFunds(buyer.address)).to.equal(depositAmount);
      expect(await escrow.verifySolvency()).to.be.true;

      // Buyer withdraws refund
      await expect(escrow.connect(buyer).withdraw())
        .to.emit(escrow, "Withdrawal")
        .withArgs(buyer.address, depositAmount);
    });

    it("should permit arbiter to resolve dispute in favor of seller", async function () {
      await escrow.connect(buyer).raiseDispute();

      await expect(escrow.connect(arbiter).resolveDispute(false))
        .to.emit(escrow, "Resolved")
        .withArgs(5, seller.address, depositAmount); // State.ResolvedToSeller = 5

      expect(await escrow.currentState()).to.equal(5);
      expect(await escrow.withdrawableFunds(seller.address)).to.equal(depositAmount);
    });

    it("should reject dispute resolution by unauthorized caller", async function () {
      await escrow.connect(buyer).raiseDispute();
      await expect(escrow.connect(buyer).resolveDispute(true))
        .to.be.revertedWithCustomError(escrow, "UnauthorizedCaller");
      await expect(escrow.connect(seller).resolveDispute(false))
        .to.be.revertedWithCustomError(escrow, "UnauthorizedCaller");
    });
  });

  // -------------------------------------------------------------------------
  // 5. Mutual Cancellation Workflow
  // -------------------------------------------------------------------------
  describe("Cancellation Workflow", function () {
    it("should allow buyer to cancel before funding", async function () {
      await expect(escrow.connect(buyer).cancelBeforeFunding())
        .to.emit(escrow, "Cancelled")
        .withArgs(buyer.address, 0);

      expect(await escrow.currentState()).to.equal(6); // State.Cancelled
    });

    it("should require mutual agreement to cancel once funded", async function () {
      await escrow.connect(buyer).deposit({ value: depositAmount });

      // Step 1: Buyer requests cancellation
      await expect(escrow.connect(buyer).requestCancellation())
        .to.emit(escrow, "CancellationRequested")
        .withArgs(buyer.address);

      expect(await escrow.cancellationInitiator()).to.equal(buyer.address);

      // Step 2: Buyer cannot self-confirm
      await expect(escrow.connect(buyer).confirmCancellation())
        .to.be.revertedWithCustomError(escrow, "SelfConfirmationDisallowed");

      // Step 3: Seller confirms cancellation
      await expect(escrow.connect(seller).confirmCancellation())
        .to.emit(escrow, "Cancelled")
        .withArgs(seller.address, depositAmount);

      expect(await escrow.currentState()).to.equal(6); // State.Cancelled
      expect(await escrow.withdrawableFunds(buyer.address)).to.equal(depositAmount);
      expect(await escrow.verifySolvency()).to.be.true;
    });

    it("should reject confirmCancellation if no request was made", async function () {
      await escrow.connect(buyer).deposit({ value: depositAmount });
      await expect(escrow.connect(seller).confirmCancellation())
        .to.be.revertedWithCustomError(escrow, "NoCancellationToConfirm");
    });
  });

  // -------------------------------------------------------------------------
  // 6. Pull-Payment Withdrawal Edge Cases
  // -------------------------------------------------------------------------
  describe("Withdrawal Mechanics", function () {
    it("should revert if caller has no withdrawable funds", async function () {
      await expect(escrow.connect(buyer).withdraw())
        .to.be.revertedWithCustomError(escrow, "NoWithdrawableFunds");
    });

    it("should prevent double withdrawal", async function () {
      await escrow.connect(buyer).deposit({ value: depositAmount });
      await escrow.connect(buyer).releasePayment();

      await escrow.connect(seller).withdraw();
      await expect(escrow.connect(seller).withdraw())
        .to.be.revertedWithCustomError(escrow, "NoWithdrawableFunds");
    });
  });

  // -------------------------------------------------------------------------
  // 7. Fuzz Testing
  // -------------------------------------------------------------------------
  describe("Fuzz Testing: Arbitrary Deposit Values & Attackers", function () {
    const fuzzValues = [
      ethers.parseEther("0.001"),
      ethers.parseEther("0.1"),
      ethers.parseEther("1.0"),
      ethers.parseEther("7.77"),
      ethers.parseEther("25.0"),
      ethers.parseEther("50.0"),
    ];

    it("should safely process complete escrow lifecycle across arbitrary ETH amounts", async function () {
      for (const val of fuzzValues) {
        const testEscrow = await Escrow.deploy(buyer.address, seller.address, arbiter.address, val);
        await testEscrow.waitForDeployment();

        // Deposit
        await testEscrow.connect(buyer).deposit({ value: val });
        expect(await testEscrow.currentState()).to.equal(1);

        // Release
        await testEscrow.connect(buyer).releasePayment();
        expect(await testEscrow.withdrawableFunds(seller.address)).to.equal(val);
        expect(await testEscrow.verifySolvency()).to.be.true;

        // Withdraw
        await testEscrow.connect(seller).withdraw();
        expect(await testEscrow.withdrawableFunds(seller.address)).to.equal(0);
        expect(await testEscrow.verifySolvency()).to.be.true;
      }
    });

    it("should reject arbitrary unauthorized caller attempts on all restricted methods", async function () {
      const unauthorizedSigners = [attacker, otherUser, owner];
      await escrow.connect(buyer).deposit({ value: depositAmount });

      for (const signer of unauthorizedSigners) {
        // Only buyer can release
        await expect(escrow.connect(signer).releasePayment())
          .to.be.revertedWithCustomError(escrow, "UnauthorizedCaller");

        // Only arbiter can resolve
        await expect(escrow.connect(signer).resolveDispute(true))
          .to.be.revertedWithCustomError(escrow, "UnauthorizedCaller");
      }
    });
  });
});

