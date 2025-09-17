```mermaid
flowchart TD
    S0[Shopping Cart]
    S1[Checkout]
    S2[Order Processing]
    S3[Shipped]
    S4[Delivered]
    S0 --> S1
    S1 --> S2
    S2 --> S3
    S3 --> S4

    %% Styling
    classDef initial fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef final fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef stage fill:#f3e5f5,stroke:#7b1fa2
    classDef gate fill:#fff3e0,stroke:#ef6c00
    classDef lock fill:#fce4ec,stroke:#c2185b

    class S0 initial
    class S1 stage
    class S2 stage
    class S3 stage
    class S4 final
```