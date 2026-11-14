#import "CacheIdentity.h"
#import <CommonCrypto/CommonDigest.h>

NSString *ValencedCacheIdentity(NSData *host, NSData *loader) {
    if (host.length == 0 || host.length > UINT32_MAX || loader.length > UINT32_MAX) return nil;

    CC_SHA256_CTX context;
    CC_SHA256_Init(&context);
    // Length prefix separates host and loader bytes with no ambiguous boundary.
    uint64_t length = host.length;
    CC_SHA256_Update(&context, &length, sizeof(length));
    CC_SHA256_Update(&context, host.bytes, (CC_LONG)host.length);
    if (loader.length) CC_SHA256_Update(&context, loader.bytes, (CC_LONG)loader.length);
    unsigned char digest[CC_SHA256_DIGEST_LENGTH];
    CC_SHA256_Final(digest, &context);

    NSMutableString *identity = [NSMutableString stringWithCapacity:CC_SHA256_DIGEST_LENGTH * 2];
    for (NSUInteger i = 0; i < sizeof(digest); i++) [identity appendFormat:@"%02x", digest[i]];
    return identity;
}
