import Foundation

public protocol MutationSequenceStore: Sendable {
    func loadSequence(clientDeviceId: String) async throws -> Int
    func saveSequence(_ sequence: Int, clientDeviceId: String) async throws
}

public actor InMemoryMutationSequenceStore: MutationSequenceStore {
    private var sequences: [String: Int]

    public init(sequences: [String: Int] = [:]) {
        self.sequences = sequences
    }

    public func loadSequence(clientDeviceId: String) async throws -> Int {
        sequences[clientDeviceId] ?? 0
    }

    public func saveSequence(_ sequence: Int, clientDeviceId: String) async throws {
        sequences[clientDeviceId] = max(sequence, sequences[clientDeviceId] ?? 0)
    }
}

public actor FileMutationSequenceStore: MutationSequenceStore {
    private let fileURL: URL
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    public init(fileURL: URL) {
        self.fileURL = fileURL
        self.encoder = JSONEncoder()
        self.decoder = JSONDecoder()
    }

    public func loadSequence(clientDeviceId: String) async throws -> Int {
        try readSequences()[clientDeviceId] ?? 0
    }

    public func saveSequence(_ sequence: Int, clientDeviceId: String) async throws {
        var sequences = try readSequences()
        sequences[clientDeviceId] = max(sequence, sequences[clientDeviceId] ?? 0)
        let directory = fileURL.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let data = try encoder.encode(sequences)
        try data.write(to: fileURL, options: [.atomic])
    }

    private func readSequences() throws -> [String: Int] {
        guard FileManager.default.fileExists(atPath: fileURL.path) else {
            return [:]
        }
        let data = try Data(contentsOf: fileURL)
        return try decoder.decode([String: Int].self, from: data)
    }
}
