#import <Foundation/Foundation.h>
#import "CacheIdentity.h"

static NSData *bytes(NSString *value) {
    return [value dataUsingEncoding:NSUTF8StringEncoding];
}

int main(void) {
    @autoreleasepool {
        NSString *first = ValencedCacheIdentity(bytes(@"host"), bytes(@"loader"));
        NSCAssert(first.length == 64, @"Expected a SHA-256 cache identity");
        NSCAssert([first isEqual:ValencedCacheIdentity(bytes(@"host"), bytes(@"loader"))], @"Identical bundles must reuse their cache");
        NSCAssert(![first isEqual:ValencedCacheIdentity(bytes(@"OTA update"), bytes(@"loader"))], @"An OTA update must not reuse old module IDs");
        NSCAssert(![first isEqual:ValencedCacheIdentity(bytes(@"host"), bytes(@"new loader"))], @"A loader update must not reuse old lookups");
        NSCAssert(![ValencedCacheIdentity(bytes(@"ab"), bytes(@"c")) isEqual:ValencedCacheIdentity(bytes(@"a"), bytes(@"bc"))], @"Host and loader boundaries must be distinct");
        NSCAssert(ValencedCacheIdentity(nil, bytes(@"loader")) == nil, @"Unknown host must disable disk caching");
        NSCAssert(ValencedCacheIdentity([NSData data], nil) == nil, @"Empty host must disable disk caching");
        puts("PASS: stable cache identity, OTA/loader invalidation, and unknown-host handling");
    }
    return 0;
}
