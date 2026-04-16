"""
Main entry point for the MCP-PROJECT
AI-Powered Research Paper Generator with Pydantic Validation
"""

import os
from dotenv import load_dotenv

from src.agents import PaperGeneratorAgent
from src.validators import PaperGenerationRequest

# Load environment variables
load_dotenv()


def main():
    """Run the paper generator agent with Pydantic validation."""
    
    # Create Pydantic request model for validation
    request = PaperGenerationRequest(
        topic="AI-driven Zero Trust Threat Detection",
        max_results=3,
        model_name="openai/gpt-4o-mini"
    )
    
    print(f"📝 Generation Request:")
    print(f"   Topic: {request.topic}")
    print(f"   Max Results: {request.max_results}")
    print(f"   Model: {request.model_name}\n")
    
    # Initialize the agent
    agent = PaperGeneratorAgent(model_name=request.model_name)
    
    # Generate the paper
    pdf_path, validation_result = agent.generate_paper(
        request.topic, 
        max_results=request.max_results
    )
    
    if pdf_path and validation_result:
        print(f"\n✅ Paper generation completed successfully!")
        print(f"📄 Output: {pdf_path}")
        print(f"📊 Quality Score: {validation_result.overall_quality_score:.1f}/100")
        print(f"🎯 Quality Level: {validation_result.quality_level.upper()}")
        print(f"✓ Valid: {'YES ✅' if validation_result.is_valid else 'NO ❌'}")
        
        # Show validation issues if any
        if validation_result.validation_errors:
            print("\n⚠️  Issues found:")
            for error in validation_result.validation_errors:
                print(f"   ❌ {error}")
        
        if validation_result.validation_warnings:
            print("\n⚠️  Warnings:")
            for warning in validation_result.validation_warnings:
                print(f"   ⚠️  {warning}")
        
        # Export validation metrics as JSON
        print("\n📊 Exporting validation metrics...")
        metrics_json = validation_result.model_dump_json(indent=2)
        with open("outputs/validation_metrics.json", "w") as f:
            f.write(metrics_json)
        print("   ✅ Saved to: outputs/validation_metrics.json")
        
    else:
        print("\n❌ Paper generation failed!")


if __name__ == "__main__":
    main()
