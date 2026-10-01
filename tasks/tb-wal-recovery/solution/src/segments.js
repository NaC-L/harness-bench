'use strict';

class SegmentManager {
  constructor(capacity) {
    this.capacity = capacity;
    this.segments = [];
  }

  reserveSegment() {
    let segment = this.segments[this.segments.length - 1];
    if (!segment || segment.entries.length === this.capacity) {
      if (segment) segment.closed = true;
      segment = {
        segmentId: this.segments.length + 1,
        closed: false,
        durableCount: 0,
        entries: [],
        durable: [],
      };
      this.segments.push(segment);
    }
    return segment;
  }

  appendEntry(segment, entry) {
    const index = segment.entries.length;
    segment.entries.push(entry);
    segment.durable.push(false);
    return index;
  }

  markDurable(segment, index) {
    segment.durable[index] = true;
    while (segment.durable[segment.durableCount]) segment.durableCount += 1;
  }

  snapshot() {
    return {
      segments: this.segments.map(segment => ({
        segmentId: segment.segmentId,
        closed: segment.closed,
        durableCount: segment.durableCount,
        entries: structuredClone(segment.entries),
      })),
    };
  }
}

module.exports = { SegmentManager };
