// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "ParallaxIOS",
    platforms: [
        .iOS(.v17),
        .macOS(.v14)
    ],
    products: [
        .library(name: "ParallaxDesignSystem", targets: ["ParallaxDesignSystem"]),
        .library(name: "ParallaxCore", targets: ["ParallaxCore"]),
        .library(name: "ParallaxApp", targets: ["ParallaxApp"])
    ],
    targets: [
        .target(name: "ParallaxDesignSystem"),
        .target(
            name: "ParallaxCore",
            dependencies: ["ParallaxDesignSystem"]
        ),
        .target(
            name: "ParallaxApp",
            dependencies: ["ParallaxCore", "ParallaxDesignSystem"]
        ),
        .testTarget(
            name: "ParallaxCoreTests",
            dependencies: ["ParallaxCore", "ParallaxDesignSystem"]
        ),
        .testTarget(
            name: "ParallaxAppTests",
            dependencies: ["ParallaxApp", "ParallaxCore"]
        )
    ]
)
