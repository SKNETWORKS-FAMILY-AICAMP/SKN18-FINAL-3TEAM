package com.skn18.reasoner;

import org.apache.jena.rdf.model.*;
import org.apache.jena.reasoner.Reasoner;
import org.apache.jena.reasoner.rulesys.GenericRuleReasoner;
import org.apache.jena.reasoner.rulesys.Rule;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.rdfconnection.RDFConnection;
import org.apache.jena.query.QueryExecution;
import org.apache.jena.query.QuerySolution;
import org.apache.jena.query.ResultSet;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.List;

/**
 * Jena 추론 엔진
 *
 * SWRL 대신 Jena Rules를 사용한 추론
 * 1. OWL/TTL 파일 로드
 * 2. Jena Rules 적용
 * 3. 추론 실행
 * 4. Fuseki 업로드
 */
public class JenaReasoner {

    private static final String NAMESPACE = "http://www.example.org/korean-history#";

    public static void main(String[] args) {
        if (args.length != 4) {
            System.err.println("Usage: java -jar jena-reasoner.jar <owl-file> <ttl-file> <rules-file> <fuseki-url>");
            System.err.println("Example: java -jar jena-reasoner.jar schema.owl data.ttl rules.rules http://localhost:3030/test");
            System.exit(1);
        }

        String owlFile = args[0];
        String ttlFile = args[1];
        String rulesFile = args[2];
        String fusekiUrl = args[3];

        try {
            System.out.println("=== Jena Reasoner 시작 ===");

            // 1. 모델 생성 및 데이터 로드
            Model baseModel = ModelFactory.createDefaultModel();
            System.out.println("1. OWL 스키마 로드: " + owlFile);
            RDFDataMgr.read(baseModel, owlFile, Lang.RDFXML);

            System.out.println("2. 인스턴스 데이터 로드: " + ttlFile);
            RDFDataMgr.read(baseModel, ttlFile, Lang.TURTLE);

            System.out.println("   - 총 트리플 수: " + baseModel.size());

            // 2. 규칙 로드
            System.out.println("3. Jena 규칙 로드: " + rulesFile);
            List<Rule> rules = loadRules(rulesFile);
            System.out.println("   - 총 규칙 수: " + rules.size());

            // 3. 추론 실행
            System.out.println("4. 추론 실행 중...");
            Reasoner reasoner = new GenericRuleReasoner(rules);
            reasoner.setDerivationLogging(true);

            InfModel infModel = ModelFactory.createInfModel(reasoner, baseModel);

            // 추론 강제 실행 (materialization)
            long startTime = System.currentTimeMillis();
            Model inferredModel = ModelFactory.createDefaultModel();
            inferredModel.add(infModel);
            long endTime = System.currentTimeMillis();

            System.out.println("   - 추론 완료 (" + (endTime - startTime) + "ms)");
            System.out.println("   - 추론 후 총 트리플 수: " + inferredModel.size());
            System.out.println("   - 새로 추론된 트리플 수: " + (inferredModel.size() - baseModel.size()));

            // 4. 메타데이터 추가
            System.out.println("5. 메타데이터 추가 중...");
            addMetadata(inferredModel, baseModel);

            // 5. Fuseki 업로드
            System.out.println("6. Fuseki 업로드: " + fusekiUrl);
            uploadToFuseki(inferredModel, fusekiUrl);

            System.out.println("\n=== ✅ 추론 완료 ===");
            System.out.println("Fuseki 엔드포인트: " + fusekiUrl + "/sparql");

        } catch (Exception e) {
            System.err.println("❌ 오류 발생: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }

    /**
     * Jena 규칙 파일 로드
     */
    private static List<Rule> loadRules(String rulesFile) throws IOException {
        String rulesContent = new String(Files.readAllBytes(Paths.get(rulesFile)));
        return Rule.parseRules(rulesContent);
    }

    /**
     * 메타데이터 추가
     * - source: "manual" (원본) 또는 "inferred" (추론)
     * - inferredAt: 추론 시각
     */
    private static void addMetadata(Model inferredModel, Model baseModel) {
        Property sourceProp = inferredModel.createProperty(NAMESPACE + "source");
        Property inferredAtProp = inferredModel.createProperty(NAMESPACE + "inferredAt");

        String timestamp = Instant.now().toString();

        // 먼저 모든 subject를 수집 (ConcurrentModificationException 방지)
        java.util.Set<Resource> subjects = new java.util.HashSet<>();
        StmtIterator iter = inferredModel.listStatements();
        while (iter.hasNext()) {
            Statement stmt = iter.nextStatement();
            Resource subject = stmt.getSubject();
            subjects.add(subject);
        }
        iter.close();

        // 수집한 subject들에 대해 메타데이터 추가
        for (Resource subject : subjects) {
            // 이미 메타데이터가 있으면 스킵
            if (subject.hasProperty(sourceProp)) {
                continue;
            }

            // 이 subject의 첫 번째 statement가 원본 데이터인지 확인
            StmtIterator subjectStmts = inferredModel.listStatements(subject, null, (RDFNode) null);
            boolean isOriginal = false;
            if (subjectStmts.hasNext()) {
                Statement firstStmt = subjectStmts.nextStatement();
                isOriginal = baseModel.contains(firstStmt);
            }
            subjectStmts.close();

            if (isOriginal) {
                subject.addProperty(sourceProp, "manual");
            } else {
                subject.addProperty(sourceProp, "inferred");
                subject.addProperty(inferredAtProp, timestamp);
            }
        }
    }

    /**
     * Fuseki에 데이터 업로드
     */
    private static void uploadToFuseki(Model model, String fusekiUrl) {
        try (RDFConnection conn = RDFConnection.connect(fusekiUrl)) {
            // 기존 데이터 삭제
            conn.update("CLEAR DEFAULT");

            // 새 데이터 업로드
            conn.load(model);

            // 업로드 확인 (QueryExecution 직접 사용)
            String countQuery = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }";
            String sparqlEndpoint = fusekiUrl + "/sparql";
            
            try (QueryExecution qExec = org.apache.jena.query.QueryExecutionFactory.sparqlService(sparqlEndpoint, countQuery)) {
                ResultSet results = qExec.execSelect();
                if (results.hasNext()) {
                    QuerySolution qs = results.nextSolution();
                    long count = qs.get("count").asLiteral().getLong();
                    System.out.println("   - 업로드된 트리플 수: " + count);
                }
            } catch (Exception e) {
                // 쿼리 확인 실패해도 업로드는 성공했으므로 모델 크기 출력
                System.out.println("   - 업로드된 트리플 수: " + model.size() + " (확인 쿼리 실패, 모델 크기 기준)");
            }
        }
    }
}
