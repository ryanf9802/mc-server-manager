using McServerManager.Domain.ValueObjects;

namespace McServerManager.Application.Validation;

public interface IServerPropertiesValidator
{
    ValidationResult Validate(string text);
}

