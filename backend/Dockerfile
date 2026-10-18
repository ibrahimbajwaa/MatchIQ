# Build stage: compile and package with Maven (tests run in CI, not here, so the image builds without Docker-in-Docker).
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn -B -q dependency:go-offline
COPY src ./src
RUN mvn -B -q package -DskipTests

# Run stage: just a JRE and the jar, as a non-root user.
FROM eclipse-temurin:21-jre
RUN useradd --system --create-home matchiq
USER matchiq
WORKDIR /home/matchiq
COPY --from=build /app/target/matchiq.jar app.jar
EXPOSE 8080
ENV JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=75"
ENTRYPOINT ["java", "-jar", "app.jar"]
