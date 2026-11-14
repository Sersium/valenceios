TARGET := iphone:clang:latest:16.0
ARCHS = arm64
INSTALL_TARGET_PROCESSES = Discord
THEOS_PACKAGE_SCHEME = rootless
FINALPACKAGE = 1
VERSION_CODE = 1.0.0
API_VERSION = $(shell sed -n 's/^apiVersion = "\(.*\)"/\1/p' ../gradle/libs.versions.toml)

THEOS ?= $(HOME)/theos
export THEOS

include $(THEOS)/makefiles/common.mk

TWEAK_NAME = ValencedTweak

ValencedTweak_FILES = $(wildcard Sources/*.x Sources/*.xm Sources/*.m Sources/*.mm Sources/**/*.x Sources/**/*.xm Sources/**/*.m Sources/**/*.mm)
# shortcut: inherited UIKit APIs remain available; migrate if a future SDK removes them.
ValencedTweak_CFLAGS = -fobjc-arc -Wno-error=deprecated-declarations -DPACKAGE_VERSION='@"$(THEOS_PACKAGE_BASE_VERSION)"' -DVERSION_CODE='@"$(VERSION_CODE)"' -DAPI_VERSION='@"$(API_VERSION)"' -I$(THEOS_PROJECT_DIR)/Headers
ValencedTweak_CCFLAGS = -std=c++17 -Wno-c++11-narrowing -I$(THEOS_PROJECT_DIR)/Headers
ValencedTweak_FRAMEWORKS = Foundation UIKit CoreGraphics CoreText CoreFoundation UniformTypeIdentifiers Security AuthenticationServices
ValencedTweak_LDFLAGS = -undefined dynamic_lookup -lz

ValencedTweak_LDFLAGS += -Wl,-force_load,$(VALENCED_CORE_LIB)

ifneq ($(VALENCED_BUNDLE_DIR),)
ValencedTweak_LDFLAGS += -Wl,-sectcreate,__DATA,__vbundle,$(VALENCED_BUNDLE_DIR)/valenced.bundle
ValencedTweak_LDFLAGS += -Wl,-sectcreate,__DATA,__vmanifest,$(VALENCED_BUNDLE_DIR)/manifest.json
endif

include $(THEOS_MAKE_PATH)/tweak.mk

after-stage::
	$(ECHO_NOTHING)find $(THEOS_STAGING_DIR) -name ".DS_Store" -delete$(ECHO_END)
ifneq ($(VALENCED_BUNDLE_DIR),)
	$(ECHO_NOTHING)cp $(VALENCED_BUNDLE_DIR)/valenced.bundle $(THEOS_STAGING_DIR)/Library/MobileSubstrate/DynamicLibraries/$(ECHO_END)
	$(ECHO_NOTHING)cp $(VALENCED_BUNDLE_DIR)/manifest.json $(THEOS_STAGING_DIR)/Library/MobileSubstrate/DynamicLibraries/valenced.manifest.json$(ECHO_END)
	$(ECHO_NOTHING)mkdir -p $(THEOS_STAGING_DIR)/Library/MobileSubstrate/DynamicLibraries/ValencedManifest.bundle$(ECHO_END)
	$(ECHO_NOTHING)cp $(VALENCED_BUNDLE_DIR)/manifest.json $(THEOS_STAGING_DIR)/Library/MobileSubstrate/DynamicLibraries/ValencedManifest.bundle/valenced.manifest.json$(ECHO_END)
endif
