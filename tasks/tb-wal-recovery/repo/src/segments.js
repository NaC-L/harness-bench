'use strict';

class SegmentManager {
  constructor(capacity) {
    this.capacity = capacity;
    this.segments = [];
  }

  reserveSegment() {
    let segment = this.segments[this.segments.length - 1];
    if (!segment || segment.reserved === this.capacity) {
      if (segment) segment.closed = true;
      segment = {
        segmentId: this.segments.length + 1,
        closed: false,
        durableCount: 0,
        entries: [],
        reserved: 0,
      };
      this.segments.push(segment);
    }
    segment.reserved += 1;
    return segment;
  }

  appendEntry(segment, entry) {
    segment.entries.push(entry);
  }

  markDurable(segment) {
    segment.durableCount += 1;
  }

  snapshot() {
    return {
      segments: this.segments.map(segment => ({
        segmentId: segment.segmentId,
        closed: segment.closed,
        durableCount: segment.durableCount,
        entries: segment.entries.map(entry => ({ ...entry })),
      })),
    };
  }
}

module.exports = { SegmentManager };
