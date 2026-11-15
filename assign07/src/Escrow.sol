// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Escrow
 * @author 2301AI14
 * @notice Production-grade 3-party escrow contract implementing strict state-machine transitions,
 *         checks-effects-interactions, custom errors, pull-over-push withdrawals, reentrancy guards,
 *         and mutual cancellation agreement.
 */
contract Escrow {
    // -----------------------------------------------------------------------
    // State Definitions
    // -----------------------------------------------------------------------

    enum State {
        Created,          // 0: Contract deployed, awaiting buyer deposit
        Funded,           // 1: Deposit received, awaiting release or dispute
        Released,         // 2: Terminal - Funds released to seller
        Disputed,         // 3: Dispute raised by buyer or seller, awaiting arbiter
        ResolvedToBuyer,  // 4: Terminal - Arbiter ruled in favor of buyer
        ResolvedToSeller, // 5: Terminal - Arbiter ruled in favor of seller
        Cancelled         // 6: Terminal - Cancelled prior to completion
    }

    // -----------------------------------------------------------------------
    // Immutable Roles & Parameters
    // -----------------------------------------------------------------------

    address public immutable buyer;
    address public immutable seller;
    address public immutable arbiter;
    uint256 public immutable targetDeposit;

    // -----------------------------------------------------------------------
    // Mutable State
    // -----------------------------------------------------------------------

    State public currentState;
    address public cancellationInitiator;

    // Pull-over-push liabilities
    mapping(address => uint256) public withdrawableFunds;
    uint256 public totalLiabilities;

    // Reentrancy guard state
    uint256 private _reentrancyStatus;
    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED = 2;

    // -----------------------------------------------------------------------
    // Custom Errors
    // -----------------------------------------------------------------------

    error ZeroAddressDetected();
    error RoleOverlapDetected();
    error InvalidDepositAmount();
    error UnauthorizedCaller(address caller);
    error InvalidState(State current, State expected);
    error AlreadyFunded();
    error DepositAmountMismatch(uint256 expected, uint256 received);
    error CancellationAlreadyRequested();
    error NoCancellationToConfirm();
    error SelfConfirmationDisallowed();
    error NoWithdrawableFunds();
    error TransferFailed();
    error TerminalStateReached(State state);
    error ReentrancyGuardReentrantCall();

    // -----------------------------------------------------------------------
    // Events
    // -----------------------------------------------------------------------

    event Funded(address indexed buyer, uint256 amount);
    event Released(address indexed seller, uint256 amount);
    event DisputeRaised(address indexed initiator);
    event Resolved(State finalState, address indexed beneficiary, uint256 amount);
    event CancellationRequested(address indexed initiator);
    event Cancelled(address indexed initiator, uint256 refundAmount);
    event Withdrawal(address indexed recipient, uint256 amount);

    // -----------------------------------------------------------------------
    // Modifiers
    // -----------------------------------------------------------------------

    modifier onlyBuyer() {
        if (msg.sender != buyer) revert UnauthorizedCaller(msg.sender);
        _;
    }

    modifier onlySeller() {
        if (msg.sender != seller) revert UnauthorizedCaller(msg.sender);
        _;
    }

    modifier onlyArbiter() {
        if (msg.sender != arbiter) revert UnauthorizedCaller(msg.sender);
        _;
    }

    modifier onlyBuyerOrSeller() {
        if (msg.sender != buyer && msg.sender != seller) revert UnauthorizedCaller(msg.sender);
        _;
    }

    modifier inState(State expected) {
        if (currentState != expected) revert InvalidState(currentState, expected);
        _;
    }

    modifier nonReentrant() {
        if (_reentrancyStatus == _ENTERED) revert ReentrancyGuardReentrantCall();
        _reentrancyStatus = _ENTERED;
        _;
        _reentrancyStatus = _NOT_ENTERED;
    }

    // -----------------------------------------------------------------------
    // Constructor
    // -----------------------------------------------------------------------

    constructor(
        address _buyer,
        address _seller,
        address _arbiter,
        uint256 _targetDeposit
    ) {
        if (_buyer == address(0) || _seller == address(0) || _arbiter == address(0)) {
            revert ZeroAddressDetected();
        }
        if (_buyer == _seller || _arbiter == _buyer || _arbiter == _seller) {
            revert RoleOverlapDetected();
        }
        if (_targetDeposit == 0) {
            revert InvalidDepositAmount();
        }

        buyer = _buyer;
        seller = _seller;
        arbiter = _arbiter;
        targetDeposit = _targetDeposit;
        currentState = State.Created;
        _reentrancyStatus = _NOT_ENTERED;
    }

    // -----------------------------------------------------------------------
    // State Transitions
    // -----------------------------------------------------------------------

    /**
     * @notice Funds the escrow with the exact required ETH deposit.
     * @dev Transition: Created -> Funded
     */
    function deposit() external payable onlyBuyer inState(State.Created) {
        if (msg.value != targetDeposit) {
            revert DepositAmountMismatch(targetDeposit, msg.value);
        }

        currentState = State.Funded;
        totalLiabilities += msg.value;
        emit Funded(msg.sender, msg.value);
    }

    /**
     * @notice Releases escrow funds to the seller.
     * @dev Transition: Funded -> Released (Terminal)
     */
    function releasePayment() external onlyBuyer inState(State.Funded) {
        currentState = State.Released;
        withdrawableFunds[seller] += targetDeposit;
        emit Released(seller, targetDeposit);
    }

    /**
     * @notice Raises a dispute to involve the neutral arbiter.
     * @dev Transition: Funded -> Disputed
     */
    function raiseDispute() external onlyBuyerOrSeller inState(State.Funded) {
        currentState = State.Disputed;
        emit DisputeRaised(msg.sender);
    }

    /**
     * @notice Resolves an active dispute by awarding the deposit to buyer or seller.
     * @dev Transition: Disputed -> ResolvedToBuyer or ResolvedToSeller (Terminal)
     * @param toBuyer True to refund buyer; False to pay seller.
     */
    function resolveDispute(bool toBuyer) external onlyArbiter inState(State.Disputed) {
        if (toBuyer) {
            currentState = State.ResolvedToBuyer;
            withdrawableFunds[buyer] += targetDeposit;
            emit Resolved(State.ResolvedToBuyer, buyer, targetDeposit);
        } else {
            currentState = State.ResolvedToSeller;
            withdrawableFunds[seller] += targetDeposit;
            emit Resolved(State.ResolvedToSeller, seller, targetDeposit);
        }
    }

    /**
     * @notice Cancels the escrow contract prior to funding.
     * @dev Transition: Created -> Cancelled (Terminal)
     */
    function cancelBeforeFunding() external onlyBuyer inState(State.Created) {
        currentState = State.Cancelled;
        emit Cancelled(msg.sender, 0);
    }

    /**
     * @notice Initiates a mutual cancellation request when funded.
     */
    function requestCancellation() external onlyBuyerOrSeller inState(State.Funded) {
        if (cancellationInitiator != address(0)) {
            revert CancellationAlreadyRequested();
        }
        cancellationInitiator = msg.sender;
        emit CancellationRequested(msg.sender);
    }

    /**
     * @notice Confirms a mutual cancellation request by the other party.
     * @dev Transition: Funded -> Cancelled (Terminal)
     */
    function confirmCancellation() external onlyBuyerOrSeller inState(State.Funded) {
        if (cancellationInitiator == address(0)) {
            revert NoCancellationToConfirm();
        }
        if (msg.sender == cancellationInitiator) {
            revert SelfConfirmationDisallowed();
        }

        currentState = State.Cancelled;
        withdrawableFunds[buyer] += targetDeposit;
        emit Cancelled(msg.sender, targetDeposit);
    }

    // -----------------------------------------------------------------------
    // Pull-over-Push Payment Withdrawal
    // -----------------------------------------------------------------------

    /**
     * @notice Withdraws accrued liabilities for the caller.
     * @dev Follows Checks-Effects-Interactions (CEI) pattern with reentrancy protection.
     */
    function withdraw() external nonReentrant {
        uint256 amount = withdrawableFunds[msg.sender];
        if (amount == 0) {
            revert NoWithdrawableFunds();
        }

        // Effect
        withdrawableFunds[msg.sender] = 0;
        totalLiabilities -= amount;

        // Interaction
        (bool sent, ) = payable(msg.sender).call{value: amount}("");
        if (!sent) {
            revert TransferFailed();
        }

        emit Withdrawal(msg.sender, amount);
    }



    // -----------------------------------------------------------------------
    // Invariant Verification View
    // -----------------------------------------------------------------------

    /**
     * @notice Confirms contract solvency invariant: balance matches recorded liabilities.
     */
    function verifySolvency() external view returns (bool) {
        return address(this).balance == totalLiabilities;
    }
}
