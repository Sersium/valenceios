plugins {
    alias(libs.plugins.kotlin.multiplatform)
    alias(libs.plugins.kotlin.serialization)
}
kotlin {
    iosArm64().binaries.framework {
        baseName = "ValencedCore"
        isStatic = true
    }
    iosSimulatorArm64()
    sourceSets {
        commonMain.dependencies {
            api(libs.kotlinx.coroutines.core)
            api(libs.okio)
            api(libs.kotlinx.serialization.json)
        }
        commonTest.dependencies {
            implementation(kotlin("test"))
            implementation(libs.okio.fakefilesystem)
        }
    }
}

// The native plugin API version must match the bundled JavaScript API.
val generateCoreConstants = tasks.register("generateCoreConstants") {
    val apiVersion = libs.versions.apiVersion.get()
    val outputDir = layout.buildDirectory.dir("generated/valenced/commonMain/kotlin")

    inputs.property("apiVersion", apiVersion)
    outputs.dir(outputDir)

    doLast {
        val file = outputDir.get().file("app/valenced/core/CoreConstants.kt").asFile
        file.parentFile.mkdirs()
        file.writeText(
            """
            package app.valenced.core

            /** The plugin API version, mirrored from `gradle/libs.versions.toml`. */
            internal const val API_VERSION_STRING: String = "$apiVersion"
            """.trimIndent() + "\n"
        )
    }
}

kotlin.sourceSets.commonMain {
    kotlin.srcDir(generateCoreConstants)
}
