FROM gradle:8.14.1-jdk21 AS build

WORKDIR /workspace

COPY gradle gradle
COPY gradlew gradlew.bat settings.gradle.kts build.gradle.kts gradle.properties ./

RUN chmod +x gradlew
RUN ./gradlew --no-daemon dependencies

COPY src src

RUN ./gradlew --no-daemon clean installDist \
    && install_dir="$(find build/install -mindepth 1 -maxdepth 1 -type d | head -n 1)" \
    && script_name="$(find "$install_dir/bin" -maxdepth 1 -type f ! -name '*.bat' -exec basename {} \; | head -n 1)" \
    && test -n "$install_dir" \
    && test -n "$script_name" \
    && mkdir -p /workspace/runtime \
    && cp -R "$install_dir"/. /workspace/runtime/ \
    && printf '#!/bin/sh\nexec /app/bin/%s "$@"\n' "$script_name" > /workspace/runtime/entrypoint.sh \
    && chmod +x /workspace/runtime/entrypoint.sh

FROM eclipse-temurin:21-jre-jammy

WORKDIR /app

COPY --from=build /workspace/runtime/ ./

ENTRYPOINT ["./entrypoint.sh"]
