using McServerManager.Domain.ValueObjects;

namespace McServerManager.Application.Validation;

public interface IWhitelistValidator
{
    ValidationResult Validate(string text);
}

