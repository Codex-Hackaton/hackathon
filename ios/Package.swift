// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "PenaltyDomain",
    platforms: [
        .iOS(.v17),
        .macOS(.v13),
    ],
    products: [
        .library(name: "PenaltyDomain", targets: ["PenaltyDomain"]),
        .executable(name: "PenaltyDemoApp", targets: ["PenaltyDemoApp"]),
    ],
    targets: [
        .target(name: "PenaltyDomain"),
        .executableTarget(
            name: "PenaltyDemoApp",
            dependencies: ["PenaltyDomain"]
        ),
        .testTarget(
            name: "PenaltyDomainTests",
            dependencies: ["PenaltyDomain"]
        ),
    ]
)
